from retriever.context_builder import build_context
def main():
    context = build_context("AAPL", "2024-08-05")
    print(context)

if __name__ == "__main__":
    main()