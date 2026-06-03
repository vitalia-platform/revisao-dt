import re

def normalize_doi(doi: str) -> str:
    if not doi or not isinstance(doi, str):
        return ""
    doi = doi.strip().lower()
    # Remove prefixos comuns
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    doi = re.sub(r'^doi:\s*', '', doi)
    # Remove colchetes ou caracteres lixo no final
    doi = re.sub(r'[\]\}]+$', '', doi)
    return doi

def normalize_title(title: str) -> str:
    if not title or not isinstance(title, str):
        return ""
    title = title.lower()
    # Remove pontuação
    title = re.sub(r'[^\w\s]', '', title)
    # Remove espaços extras
    title = re.sub(r'\s+', ' ', title).strip()
    return title

class Deduplicator:
    def __init__(self, master_log_path=None):
        self.seen_dois = set()
        self.seen_titles = set()
        
        if master_log_path:
            self._load_master(master_log_path)
            
    def _load_master(self, path):
        import os, csv
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = normalize_doi(row.get("DOI", ""))
                if d:
                    self.seen_dois.add(d)
                t = normalize_title(row.get("Title", ""))
                if t:
                    self.seen_titles.add(t)

    def is_duplicate(self, article: dict) -> bool:
        """Retorna True se o artigo já foi processado (verificando DOI e Título)."""
        doi = normalize_doi(article.get("doi", ""))
        title = normalize_title(article.get("title", ""))
        
        if doi and doi in self.seen_dois:
            return True
            
        if title and title in self.seen_titles:
            return True
            
        return False

    def add_to_seen(self, article: dict):
        """Adiciona o artigo ao conjunto de artigos vistos (para deduplicação inline)."""
        doi = normalize_doi(article.get("doi", ""))
        title = normalize_title(article.get("title", ""))
        if doi: self.seen_dois.add(doi)
        if title: self.seen_titles.add(title)
