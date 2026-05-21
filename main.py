from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from datetime import date

app = FastAPI(title="TaxLink Taiwan Core Engine API")

# Paste your Enums here (HousingStatus, IncomeCategory, etc.)
class HousingStatus(str, Enum):
    TENANCY = "Tenancy"
    OWNERSHIP = "Ownership"
    OTHER = "Other"

# Define what a secure data payload looks like
class TaxpayerProfile(BaseModel):
    full_name: str
    id_number: str
    email: EmailStr
    dob: date
    housing_status: HousingStatus

# This is your secure endpoint where the frontend will send data
@app.post("/api/v1/calculate")
def calculate_taiwan_tax(profile: TaxpayerProfile):
    try:
        # Move your math logic from your streamlit app here
        # e.g., base_tax = calculate_brackets(profile)
        return {"status": "success", "tax_liability": 0, "msg": "Engine verified"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))