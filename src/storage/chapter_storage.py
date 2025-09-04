import sqlite3
from datetime import date
from typing import List, Optional
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from src.core.memory_interface import Chapter


class ChapterStorage:
    def __init__(self, db_path='chapters.db', faiss_index_path='chapters.faiss', embedding_model_name='all-MiniLM-L6-v2'):
        self.db_path = db_path
        self.faiss_index_path = faiss_index_path
        self.conn = sqlite3.connect(self.db_path,check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.model = SentenceTransformer(embedding_model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self._create_tables()
        self._load_faiss_index()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT,
                memory TEXT,
                tags TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS faiss_map (
                chapter_id INTEGER PRIMARY KEY,
                faiss_id INTEGER
            )
        ''')
        self.conn.commit()

    def _load_faiss_index(self):
        try:
            self.index = faiss.read_index(self.faiss_index_path)
            self.next_faiss_id = self.index.ntotal
        except:
            # create new index if not exists
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # inner product
            self.next_faiss_id = 0

    def save(self, chapter: Chapter):
        """Save chapter metadata + embedding"""
        # Save chapter metadata
        tags_json = json.dumps(chapter.tags) if chapter.tags else None
        self.cursor.execute('''
            INSERT INTO chapters (day, memory, tags) VALUES (?, ?, ?)
        ''', (chapter.day.isoformat(), chapter.memory, tags_json))
        chapter_id = self.cursor.lastrowid
        self.conn.commit()

        # Compute embedding
        embedding = self.model.encode(chapter.memory, convert_to_numpy=True)
        embedding = embedding / np.linalg.norm(embedding)  # normalize for cosine similarity

        # Add to FAISS
        self.index.add(np.expand_dims(embedding, axis=0))
        faiss_id = self.next_faiss_id
        self.next_faiss_id += 1

        # Map chapter_id to faiss_id
        self.cursor.execute('''
            INSERT INTO faiss_map (chapter_id, faiss_id) VALUES (?, ?)
        ''', (chapter_id, faiss_id))
        self.conn.commit()

        # Save FAISS index to disk
        faiss.write_index(self.index, self.faiss_index_path)

    def retrieve_by_day(self, day: date) -> List[Chapter]:
        """Get all chapters for a given day"""
        self.cursor.execute('SELECT memory, tags, day FROM chapters WHERE day = ?', (day.isoformat(),))
        rows = self.cursor.fetchall()
        return [Chapter(day=date.fromisoformat(r[2]), memory=r[0], tags=json.loads(r[1]) if r[1] else None) for r in rows]

    def semantic_retrieve(self, query: str, top_k: int = 5, day_filter: Optional[date] = None) -> List[dict]:
        """Retrieve chapters semantically using FAISS + optional day filter"""
        query_emb = self.model.encode(query, convert_to_numpy=True)
        query_emb = query_emb / np.linalg.norm(query_emb)

        # Search FAISS
        D, I = self.index.search(np.expand_dims(query_emb, axis=0), top_k*3)  # get extra in case day filter reduces results
        retrieved = []

        for faiss_id, score in zip(I[0], D[0]):
            if faiss_id == -1:
                continue
            # Map faiss_id -> chapter_id
            self.cursor.execute('SELECT chapter_id FROM faiss_map WHERE faiss_id = ?', (faiss_id,))
            res = self.cursor.fetchone()
            if not res:
                continue
            chapter_id = res[0]
            # Fetch chapter metadata
            self.cursor.execute('SELECT memory, tags, day FROM chapters WHERE id = ?', (chapter_id,))
            row = self.cursor.fetchone()
            if not row:
                continue
            chap_day = date.fromisoformat(row[2])
            if day_filter and chap_day != day_filter:
                continue
            chapter = Chapter(day=chap_day, memory=row[0], tags=json.loads(row[1]) if row[1] else None)
            retrieved.append({"chapter": chapter, "score": float(score)})

        # Sort: latest day first, then score
        retrieved.sort(key=lambda x: (x["chapter"].day, x["score"]), reverse=True)
        return retrieved[:top_k]
    
    def get_last_chapter(self) -> Chapter | None:
        """Return the most recently saved chapter"""
        self.cursor.execute('''
            SELECT memory, tags, day FROM chapters
            ORDER BY id DESC
            LIMIT 1
        ''')
        row = self.cursor.fetchone()
        if not row:
            return None
        return Chapter(
            day=date.fromisoformat(row[2]),
            memory=row[0],
            tags=json.loads(row[1]) if row[1] else None
        )
        
        
    def semantic_retrieve_global(self, query: str, top_k: int = 5) -> List[dict]:
        """Search globally across all chapters in FAISS"""
        query_emb = self.model.encode(query, convert_to_numpy=True)
        query_emb = query_emb / np.linalg.norm(query_emb)

        D, I = self.index.search(np.expand_dims(query_emb, axis=0), top_k)
        results = []
        for faiss_id, score in zip(I[0], D[0]):
            if faiss_id == -1:
                continue
            # Map faiss_id -> chapter_id
            self.cursor.execute('SELECT chapter_id FROM faiss_map WHERE faiss_id = ?', (faiss_id,))
            res = self.cursor.fetchone()
            if not res:
                continue
            chapter_id = res[0]
            self.cursor.execute('SELECT memory, tags, day FROM chapters WHERE id = ?', (chapter_id,))
            row = self.cursor.fetchone()
            if not row:
                continue
            results.append({
                "chapter": Chapter(
                    day=date.fromisoformat(row[2]),
                    memory=row[0],
                    tags=json.loads(row[1]) if row[1] else None
                ),
                "score": float(score)
            })
        return results


    def semantic_retrieve_range(self, query: str, start: date, end: date, top_k: int = 5) -> List[dict]:
        """Retrieve semantically but restricted to chapters in [start, end]"""
        # 1. Fetch all chapters in range
        self.cursor.execute('''
            SELECT id, memory, tags, day FROM chapters
            WHERE day BETWEEN ? AND ?
        ''', (start.isoformat(), end.isoformat()))
        rows = self.cursor.fetchall()
        if not rows:
            return []

        # 2. Build temporary embeddings + FAISS index for this subset
        memories = [r[1] for r in rows]
        ids = [r[0] for r in rows]
        emb = self.model.encode(memories, convert_to_numpy=True, show_progress_bar=False)
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)

        sub_index = faiss.IndexFlatIP(self.embedding_dim)
        sub_index.add(emb)

        # 3. Query
        query_emb = self.model.encode(query, convert_to_numpy=True)
        query_emb = query_emb / np.linalg.norm(query_emb)
        D, I = sub_index.search(np.expand_dims(query_emb, axis=0), min(top_k, len(ids)))

        # 4. Collect results
        results = []
        for idx, score in zip(I[0], D[0]):
            row = rows[idx]
            results.append({
                "chapter": Chapter(
                    day=date.fromisoformat(row[3]),
                    memory=row[1],
                    tags=json.loads(row[2]) if row[2] else None
                ),
                "score": float(score)
            })

        return results
    
    def semantic_retrieve_day(self, query: str, day: date, top_k: int = 5) -> List[dict]:
        """Semantic retrieve but restricted to a single day"""
        return self.semantic_retrieve_range(query, start=day, end=day, top_k=top_k)

