from sqlmodel import Field, SQLModel

class ProductBase(SQLModel):
    name: str = Field(index=True)
    description: str | None = None
    price: float = Field(..., gt=0)  # Ensures price is greater than 0
    quantity: int = Field(default=0, ge=0)  # Ensures quantity is 0 or more

class Product(ProductBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

class ProductCreate(ProductBase):
    pass

class ProductPublic(ProductBase):
    id: int

class ProductUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, gt=0)  # Ensure updated price is greater than 0
    quantity: int | None = Field(default=None, ge=0)  # Ensure updated quantity is 0 or more
   