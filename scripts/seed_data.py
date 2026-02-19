from backend.rag import RAGRetriever


def main():
    retriever = RAGRetriever()
    retriever.load_corpus()
    print("Seeded ChromaDB corpus")


if __name__ == "__main__":
    main()
