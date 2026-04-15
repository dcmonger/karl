"""ChromaDB for unstructured data - preferences, recipes, feedback."""
import chromadb
from chromadb.config import Settings
from typing import Optional
import json
import os

CHROMA_PATH = "kitchen_agent/storage/chroma"

def init_vector_store():
    os.makedirs(CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PATH)

class PreferenceStore:
    def __init__(self):
        self.client = init_vector_store()
        self.collection = self.client.get_or_create_collection("preferences")
    
    def add_preference(self, user_id: str, preference_type: str, 
                       entity: str, value: str, notes: str = None):
        doc = json.dumps({
            "user_id": user_id,
            "type": preference_type,
            "entity": entity,
            "value": value,
            "notes": notes
        })
        self.collection.add(
            documents=[doc],
            metadatas=[{"user_id": user_id, "type": preference_type, "entity": entity}],
            ids=[f"{user_id}_{preference_type}_{entity}"]
        )
    
    def get_preferences(self, user_id: str, preference_type: str = None) -> list:
        where = {"user_id": user_id}
        if preference_type:
            where["type"] = preference_type
        
        results = self.collection.get(where=where)
        return [json.loads(doc) for doc in results.get("documents", [])]
    
    def search_preferences(self, user_id: str, query: str, limit: int = 5) -> list:
        results = self.collection.query(
            query_texts=[query],
            where={"user_id": user_id},
            n_results=limit
        )
        return [json.loads(doc) for doc in results.get("documents", [[]])[0]]

class RecipeHistoryStore:
    def __init__(self):
        self.client = init_vector_store()
        self.collection = self.client.get_or_create_collection("recipe_history")
    
    def add_recipe(self, user_id: str, recipe_name: str, ingredients: list,
                   feedback: str = None, rating: int = None):
        doc = json.dumps({
            "user_id": user_id,
            "recipe_name": recipe_name,
            "ingredients": ingredients,
            "feedback": feedback,
            "rating": rating
        })
        import time
        self.collection.add(
            documents=[doc],
            metadatas=[{"user_id": user_id, "recipe_name": recipe_name}],
            ids=[f"{user_id}_{recipe_name}_{int(time.time())}"]
        )
    
    def get_recent_recipes(self, user_id: str, limit: int = 10) -> list:
        results = self.collection.get(where={"user_id": user_id})
        return [json.loads(doc) for doc in results.get("documents", [])][-limit:]
    
    def search_recipes(self, user_id: str, query: str, limit: int = 5) -> list:
        results = self.collection.query(
            query_texts=[query],
            where={"user_id": user_id},
            n_results=limit
        )
        return [json.loads(doc) for doc in results.get("documents", [[]])[0]]

class InventoryDescriptionStore:
    def __init__(self):
        self.client = init_vector_store()
        self.collection = self.client.get_or_create_collection("inventory_descriptions")
    
    def add_description(self, item_name: str, description: str, category: str = None):
        doc = json.dumps({
            "item_name": item_name,
            "description": description,
            "category": category
        })
        self.collection.add(
            documents=[doc],
            metadatas=[{"item_name": item_name, "category": category}],
            ids=[f"item_{item_name}"]
        )
    
    def get_description(self, item_name: str) -> Optional[dict]:
        results = self.collection.get(ids=[f"item_{item_name}"])
        if results["documents"]:
            return json.loads(results["documents"][0])
        return None
    
    def search_items(self, query: str, limit: int = 10) -> list:
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        return [json.loads(doc) for doc in results.get("documents", [[]])[0]]
