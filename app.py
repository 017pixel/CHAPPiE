from api.main import app


def main():
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8010, reload=True)


if __name__ == "__main__":
    main()
