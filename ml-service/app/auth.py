from fastapi import Header, HTTPException, status

ML_API_KEY: str | None = None


def set_api_key(key: str) -> None:
    global ML_API_KEY
    ML_API_KEY = key


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    if ML_API_KEY and x_api_key != ML_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_api_key
