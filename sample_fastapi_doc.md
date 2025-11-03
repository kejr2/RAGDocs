# FastAPI Documentation

## What is FastAPI?

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.

The key features are:

- Fast: Very high performance, on par with NodeJS and Go
- Fast to code: Increase the speed to develop features by about 200% to 300%
- Fewer bugs: Reduce about 40% of human (developer) induced errors
- Intuitive: Great editor support with completion everywhere
- Easy: Designed to be easy to use and learn
- Short: Minimize code duplication
- Robust: Get production-ready code
- Standards-based: Based on (and fully compatible with) open standards for APIs: OpenAPI and JSON Schema

## Installation

To install FastAPI, you need to install it along with an ASGI server:

```bash
pip install fastapi
pip install "uvicorn[standard]"
```

## Creating Your First API

Here's a simple example of creating a FastAPI application:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

## Running the Application

To run your FastAPI application:

```bash
uvicorn main:app --reload
```

The `--reload` flag makes the server restart after code changes. Use it only for development.

## Path Parameters

FastAPI supports path parameters with type hints:

```python
@app.get("/users/{user_id}")
async def read_user(user_id: int):
    return {"user_id": user_id}
```

## Query Parameters

Query parameters are the key-value pairs that go after the `?` in a URL:

```python
@app.get("/items/")
async def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

## Request Body

To declare a request body, you use Pydantic models:

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

@app.post("/items/")
async def create_item(item: Item):
    return item
```

## Automatic Documentation

FastAPI automatically generates interactive API documentation. After running your app, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Validation

FastAPI provides automatic validation using Pydantic:

```python
from typing import Optional
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
```

## Conclusion

FastAPI makes it easy to build APIs quickly with automatic documentation, validation, and high performance.

