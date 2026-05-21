import streamlit as st
from enum import Enum
from typing import List, Optional
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field, EmailStr

# ==========================================
# 1. ENUMS & CONSTANTS (Taiwan Tax Rules 2025/2026)
# ==========================================
class HousingStatus(str, Enum):
    TENANCY = "Tenancy"
    OWNERSHIP = "Ownership"
    OTHER = "Other"

class IncomeCategory(str, Enum):
    SALARY = "Category 1: Employment Salaries (薪資所得)"
    PROFESSIONAL = "Category 2: Professional Practice (執行業務所得)"
    PROPERTY_LEASING = "Category 3: Property Leasing & Royalties (租賃所得及權利金)"
    SELF_UNDERTAKING = "Category 4: Farming, Fishing, Mining, Animal Husbandry (自力營耕、漁、牧、林、礦)"
    PROPERTY_TRANSACTION = "Category 5: Property Transactions / Capital Gains (財產交易所得)"
    CONTEST_PRIZES = "Category 6: Contests, Games, Prizes (競技、競賽及機會中獎之獎金)"
    RETIREMENT = "Category 7: Separation/Retirement Pay (退職所得)"
    OTHER = "Category 8: Other Income (其他所得)"
    VIRTUAL_DIVIDENDS = "Category 9: Dividends / Cooperative Earnings (股利及合作社盈餘)"
    BUSINESS_PROFIT = "Category 10: Profit from Variable Business Operations (營利所得)"

AMT_EXEMPTION_THRESHOLD = Decimal("7500000")  # 7.5 Million TWD exemption floor
AMT_TAX_RATE = Decimal("0.20")                # 20% flat AMT rate
# Statutory constants
STANDARD_DEDUCTION_SINGLE = Decimal("131000")
STANDARD_DEDUCTION_MARRIED = Decimal("262000")
SAVINGS_INVESTMENT_CAP = Decimal("270000")
# Statutory constants
STANDARD_DEDUCTION_SINGLE = Decimal("131000")
STANDARD_DEDUCTION_MARRIED = Decimal("262000")
SAVINGS_INVESTMENT_CAP = Decimal("270000")
# Paste these here:
BASE_EXEMPTION = Decimal("97000")             # Updated statutory base for 2026 season
ELDERLY_EXEMPTION = Decimal("145500")          # Updated elderly base for 2026 season
DIVIDEND_CREDIT_RATE = Decimal("0.085")       # 8.5% Tax Credit
DIVIDEND_CREDIT_CAP = Decimal("80000")        # Max $80,000 TWD credit cap
DIVIDEND_SEPARATE_RATE = Decimal("0.28")      # 28% Separate Flat Tax Rate
# ==========================================
# 2. DATA MODELS & SCHEMAS
# ==========================================
class Dependent(BaseModel):
    name: str
    relationship: str  # Lineal ascendant, Child, Sibling, etc.
    id_number: str
    date_of_birth: date
    is_handicapped: bool = False

class TravelRecord(BaseModel):
    entry_date: date
    departure_date: date
    days_calculated: int

class TaxpayerProfile(BaseModel):
    full_name: str
    id_number: str
    sex_nationality: str
    passport_number: Optional[str] = None
    tax_jurisdiction_code: str = "Taiwan (ROC)"
    date_of_birth: date
    residence_address: str
    contact_address: str
    email: EmailStr
    telephone: str
    housing_status: HousingStatus
    spouse_name: Optional[str] = None
    spouse_id: Optional[str] = None
    dependents: List[Dependent] = []
    filed_past_five_years: bool
    last_filing_year: Optional[int] = None
    receipt_number: Optional[str] = None
    travel_history: List[TravelRecord] = []

class IncomeEntry(BaseModel):
    category: IncomeCategory
    source_entity_details: str
    gross_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    withholding_tax: Decimal = Field(default=Decimal("0.00"), ge=0)

class DeductionsRegistry(BaseModel):
    is_married: bool = False
    use_itemized: bool = False
    donations: Decimal = Field(default=Decimal("0.00"), ge=0)
    insurance_premiums: Decimal = Field(default=Decimal("0.00"), ge=0)
    medical_maternity: Decimal = Field(default=Decimal("0.00"), ge=0)
    mortgage_interest: Decimal = Field(default=Decimal("0.00"), ge=0)
    savings_and_investment: Decimal=Field(default=Decimal("0.00"), ge=0)
    educational_tuition: Decimal = Field(default=Decimal("0.00"), ge=0)
    pre_school_children: Decimal = Field(default=Decimal("0.00"), ge=0)
    housing_rent: Decimal = Field(default=Decimal("0.00"), ge=0)
    property_transaction_losses: Decimal = Field(default=Decimal("0.00"), ge=0)
    foreign_income: Decimal = Field(default=Decimal("0.00"), ge=0)
    insurance_benefits: Decimal = Field(default=Decimal("0.00"), ge=0)
    private_securities: Decimal = Field(default=Decimal("0.00"), ge=0)
    has_salary_income: bool = False
    disability_count: int = Field(default=0, ge=0)
    long_term_care_count: int = Field(default=0, ge=0)
    dividend_income: Decimal = Field(default=Decimal("0.00"), ge=0)

class BankDetails(BaseModel):
    bank_name_branch: str
    account_number: str
    account_type_code: str
    waive_physical_check: bool = False

class TaxFilingSession(BaseModel):
    profile: TaxpayerProfile
    income_entries: List[IncomeEntry]
    deductions: DeductionsRegistry
    bank_details: Optional[BankDetails] = None

# ==========================================
# 3. CORE TAX CALCULATION ENGINE
# ==========================================
class TaxCalculator:
    @staticmethod
    def calculate(session: TaxFilingSession) -> dict:
        total_gross_income = sum(item.gross_amount for item in session.income_entries)
        total_withholding_tax = sum(item.withholding_tax for item in session.income_entries)
        
        # --- A. CALCULATE PERSONAL EXEMPTIONS ---
        current_year = 2026
        total_exemptions = Decimal("0")
        
        # 1. Taxpayer Exemption
        taxpayer_age = current_year - session.profile.date_of_birth.year
        if taxpayer_age >= 70:
            total_exemptions += Decimal("145500")
        else:
            total_exemptions += Decimal("97000")
            
        # 2. Spouse Exemption (if married)
        if session.deductions.is_married:
            total_exemptions += Decimal("97000")
            
        # 3. Dependents Exemption Matrix
        for dep in session.profile.dependents:
            dep_age = current_year - dep.date_of_birth.year
            if dep_age >= 70:
                total_exemptions += Decimal("145500")
            else:
                total_exemptions += Decimal("97000")
                
        # Count household size for the BLE calculation below
        household_count = 1 + (1 if session.deductions.is_married else 0) + len(session.profile.dependents)

        # --- B. DETERMINE BASE DEDUCTION ---
        if session.deductions.use_itemized:
            base_deduction = (
                session.deductions.donations +
                session.deductions.insurance_premiums +
                session.deductions.medical_maternity +
                session.deductions.mortgage_interest
            )
        else:
            base_deduction = (
                Decimal("262000") if session.deductions.is_married 
                else Decimal("131000")
            )
            
       # --- C. SPECIAL DEDUCTIONS WITH CAPS ---
        savings_deduction = min(session.deductions.savings_and_investment, Decimal("270000"))
        
        # 1. Salary Income Deduction (Automatically capped at $218,000 max if salary exists)
        # Note: In a fully complete app, this would cap against the actual gross salary amount reported.
        salary_deduction = Decimal("218000") if session.deductions.has_salary_income else Decimal("0")
        
        # 2. Disability Deduction ($218,000 per certified household member)
        disability_deduction = Decimal(str(session.deductions.disability_count)) * Decimal("218000")
        
        # 3. Long-Term Care Deduction ($120,000 per qualified household member)
        ltc_deduction = Decimal(str(session.deductions.long_term_care_count)) * Decimal("120000")
        
        # --- D. DYNAMIC BASIC LIVING EXPENSE SAFETY NET ---
        total_household_ble = Decimal(str(household_count)) * Decimal("213000")
        
        ble_comparison_total = (
            total_exemptions +
            base_deduction +
            savings_deduction +
            session.deductions.educational_tuition +
            session.deductions.pre_school_children +
            session.deductions.housing_rent +
            disability_deduction +
            ltc_deduction
        )
        
        ble_difference_allowance = max(total_household_ble - ble_comparison_total, Decimal("0.00"))

        # --- E. AGGREGATE TOTAL APPLIED DEDUCTIONS ---
        total_deductions = (
            base_deduction +
            savings_deduction +
            salary_deduction +
            disability_deduction +
            ltc_deduction +
            session.deductions.educational_tuition +
            session.deductions.pre_school_children +
            session.deductions.housing_rent +
            ble_difference_allowance
        )
        
# --- F. THE GREAT DIVIDEND SPLIT ENGINE OPTIMIZATION ---
        # 1. OPTION A: CONSOLIDATED METHOD (Dividends included in progressive pool, 8.5% credit back)
        consolidated_net_income = max((total_gross_income + session.deductions.dividend_income) - total_exemptions - total_deductions, Decimal("0.00"))
        
        # Calculate Progressive Base for Option A
        if consolidated_net_income <= Decimal("590000"):
            gross_prog_a = consolidated_net_income * Decimal("0.05")
        elif consolidated_net_income <= Decimal("1330000"):
            gross_prog_a = (consolidated_net_income * Decimal("0.12")) - Decimal("41300")
        elif consolidated_net_income <= Decimal("2660000"):
            gross_prog_a = (consolidated_net_income * Decimal("0.20")) - Decimal("147700")
        elif consolidated_net_income <= Decimal("4980000"):
            gross_prog_a = (consolidated_net_income * Decimal("0.30")) - Decimal("413700")
        else:
            gross_prog_a = (consolidated_net_income * Decimal("0.40")) - Decimal("911700")
            
        # Apply the 8.5% tax credit capped at $80,000 TWD
        dividend_credit = min(session.deductions.dividend_income * DIVIDEND_CREDIT_RATE, DIVIDEND_CREDIT_CAP)
        final_tax_option_a = max(gross_prog_a - dividend_credit, Decimal("0.00"))


        # 2. OPTION B: SEPARATED METHOD (Dividends pulled out completely, taxed at flat 28%)
        separated_net_income = max(total_gross_income - total_exemptions - total_deductions, Decimal("0.00"))
        
        # Calculate Progressive Base for Option B
        if separated_net_income <= Decimal("590000"):
            gross_prog_b = separated_net_income * Decimal("0.05")
        elif separated_net_income <= Decimal("1330000"):
            gross_prog_b = (separated_net_income * Decimal("0.12")) - Decimal("41300")
        elif separated_net_income <= Decimal("2660000"):
            gross_prog_b = (separated_net_income * Decimal("0.20")) - Decimal("147700")
        elif separated_net_income <= Decimal("4980000"):
            gross_prog_b = (separated_net_income * Decimal("0.30")) - Decimal("413700")
        else:
            gross_prog_b = (separated_net_income * Decimal("0.40")) - Decimal("911700")
            
        # Add flat 28% dividend tax
        dividend_flat_tax = session.deductions.dividend_income * DIVIDEND_SEPARATE_RATE
        final_tax_option_b = gross_prog_b + dividend_flat_tax


        # 3. SELECT OPTIMIZED STRATEGY AUTOMATICALLY
        if final_tax_option_a <= final_tax_option_b:
            chosen_strategy = "CONSOLIDATED (合併申報 - Recommended)"
            gross_tax_payable = final_tax_option_a
            net_taxable_income = consolidated_net_income
        else:
            chosen_strategy = "SEPARATED (分開計稅 - Recommended for High Income)"
            gross_tax_payable = final_tax_option_b
            net_taxable_income = separated_net_income

        # --- G. ALTERNATIVE MINIMUM TAX (AMT) ASSESSMENT ---
        effective_foreign_income = session.deductions.foreign_income if session.deductions.foreign_income >= Decimal("1000000") else Decimal("0")
        basic_income = net_taxable_income + effective_foreign_income + session.deductions.insurance_benefits + session.deductions.private_securities
        basic_tax_payable = max(basic_income - Decimal("7500000"), Decimal("0.00")) * Decimal("0.20")
        
        if basic_tax_payable > gross_tax_payable:
            amt_supplementary_due = basic_tax_payable - gross_tax_payable
            final_tax_liability = basic_tax_payable
        else:
            amt_supplementary_due = Decimal("0.00")
            final_tax_liability = gross_tax_payable
            
        estimated_balance = total_withholding_tax - final_tax_liability

        return {
            "total_gross_income": total_gross_income,
            "total_exemptions": total_exemptions,
            "total_deductions": total_deductions,
            "ble_safety_net": ble_difference_allowance,
            "net_taxable_income": net_taxable_income,
            "gross_tax_payable": gross_tax_payable,
            "total_withholding_credits": total_withholding_tax,
            "basic_income": basic_income,
            "basic_tax_payable": basic_tax_payable,
            "amt_supplementary_due": amt_supplementary_due,
            "final_tax_liability": final_tax_liability,
            "balance_status": "REFUND" if estimated_balance > 0 else "BALANCE_DUE",
            "final_reconciliation_amount": abs(estimated_balance),
            "chosen_strategy": chosen_strategy,
            "final_reconciliation_amount": abs(estimated_balance)
        }

# ==========================================
# 4. INTERACTIVE USER INTERFACE (Streamlit Replacement)
# ==========================================
st.set_page_config(page_title="TaxLink Taiwan Engine", layout="wide")

st.title("TaxLink Taiwan Engine")
st.subheader("Interactive Tax Reconciliation Tool")


# 1. Initialize the tabs here
tab_profile, tab_income, tab_deductions, tab_amt, tab_reconcile = st.tabs([
    "👤 1. Family Profile", 
    "💰 2. Income Declaration", 
    "📝 3. Deductions & Exemptions",
    "🏢 4. AMT (Alternative Minimum Tax)",
    "📊 5. Summary & Refund Method"
])

# 2. Group your profile inputs inside the first tab
with tab_profile:
    st.subheader("Taxpayer, Spouse, and Dependent Logistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        full_name = st.text_input("Full Name", value="John Doe")
        id_number = st.text_input("ID Number (ARC/National ID)", value="A123456789")
        email_input = st.text_input("Email Address", value="john.doe@example.com")
    with col2:
        dob = st.date_input("Date of Birth", value=date(1990, 1, 1))
        telephone = st.text_input("Telephone Contact", value="0912345678")
        h_status = st.selectbox("Housing Status", [status.value for status in HousingStatus])
    with col3:
        sex_nat = st.text_input("Sex / Nationality", value="M / Taiwan (ROC)")
        res_addr = st.text_input("Residence Address", value="123 Xinyi Rd, Taipei")
        cont_addr = st.text_input("Contact Address", value="123 Xinyi Rd, Taipei")

# 3. Group your income inputs inside the second tab
with tab_income:
    st.subheader("Itemized Income Categories & Withholding Receipts")
    st.write("Enter all your income streams below. Click **＋ Add row** at the bottom of the table to add more receipts.")
    
    # Paste your dynamic editor here!
    edited_income_df = st.data_editor(
        data=[{
            "Category": "Category 1: Employment Salaries (薪資所得)", 
            "Company": "ACME Corp", 
            "Gross Amount": 1200000, 
            "Withholding": 45000
        }],
        num_rows="dynamic",
        use_container_width=True
    )
    
    # We will temporarily use the first row to keep your engine running seamlessly
    if len(edited_income_df) > 0:
        first_row = edited_income_df[0]
        inc_category = first_row.get("Category", "Category 1: Employment Salaries (薪資所得)")
        entity = first_row.get("Company", "")
        gross_amt = first_row.get("Gross Amount", 0)
        withholding = first_row.get("Withholding", 0)
    else:
        inc_category = "Category 1: Employment Salaries (薪資所得)"
        entity = ""
        gross_amt = 0
        withholding = 0

# 4. Group your deduction inputs inside the third tab
with tab_deductions:
    st.subheader("Deductions & Allowances Registry")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Filing Status:**")
        is_married = st.checkbox("Filing Status: Married / Joint Filing", value=False)
        use_itemized = st.checkbox("Opt for Itemized Deductions (Instead of Standard)", value=False)
        
        st.write("---")
        st.write("**Special Deductions (特別扣除額):**")
        has_salary = st.checkbox("Include Salary Special Deduction ($218,000 limit)", value=True)
        savings_inv = st.number_input("Savings and Investment Deductions", min_value=0, value=50000)
        disability_cnt = st.number_input("Number of members with Disability Handbooks", min_value=0, max_value=10, value=0)
        ltc_cnt = st.number_input("Number of members qualifying for Long-Term Care", min_value=0, max_value=10, value=0)
        edu_tuition = st.number_input("Educational Tuition Deductions", min_value=0, value=0)
        pre_school = st.number_input("Pre-school Children Deductions", min_value=0, value=0)
        house_rent = st.number_input("Housing Rent Deduction", min_value=0, value=0)
        
    with col2:
        if use_itemized:
            st.write("**Itemized Deduction Options:**")
            donations = st.number_input("Donations Outlay", min_value=0, value=0)
            insurance = st.number_input("Insurance Premiums", min_value=0, value=0)
            medical = st.number_input("Medical & Maternity Expenses", min_value=0, value=0)
            mortgage = st.number_input("Mortgage Interest (Self-Use Housing)", min_value=0, value=0)
        else:
            st.write("**Standard Deduction Active:**")
            deduct_val = Decimal("262000") if is_married else Decimal("131000")
            st.info(f"Using statutory baseline deduction: **${deduct_val:,} TWD**")
            # Assign fallback zeros so variables exist for the engine regardless
            donations, insurance, medical, mortgage = Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")

# 5. Placeholders for your newly planned tabs
with tab_amt:
    st.subheader("Alternative Minimum Tax (AMT) / Income Basic Tax Assessment")
    st.write("Declare items that are excluded from regular progressive tax but subject to basic income tax calculation rules:")
    
    col1, col2 = st.columns(2)
    with col1:
        amt_foreign = st.number_input("Foreign-Sourced Income (Overseas Income)", min_value=0, value=0, step=50000,
                                      help="Declare if total household foreign income is equal to or greater than $1,000,000 TWD.")
        amt_insurance = st.number_input("Non-Qualified Life/Injury Insurance Benefits", min_value=0, value=0, step=10000)
    with col2:
        amt_securities = st.number_input("Private Placement Securities Transaction Gains", min_value=0, value=0, step=10000)
        
    # Visual checklist indicator rule
    if amt_foreign > 0 and amt_foreign < 1000000:
        st.warning("⚠️ Note: If total household foreign income is less than $1,000,000 TWD, it does not need to be calculated into basic income.")

# ==========================================
# 5. ENGINE TRIGGERS & EVALUATION
# ==========================================
st.write("---")
if st.button("⚡ Run Tax Engine Calculation", type="primary", use_container_width=True):
    try:
        # 1. Validate structure on-the-fly inside Pydantic structures
        profile_instance = TaxpayerProfile(
            full_name=full_name, id_number=id_number, sex_nationality=sex_nat,
            date_of_birth=dob, residence_address=res_addr, contact_address=cont_addr,
            email=email_input, telephone=telephone, housing_status=HousingStatus(h_status),
            filed_past_five_years=False
        )
        
        income_instances = [
            IncomeEntry(
                category=IncomeCategory(inc_category), 
                source_entity_details=entity, 
                gross_amount=Decimal(str(gross_amt)), 
                withholding_tax=Decimal(str(withholding))
            )
        ]
        
        deductions_instance = DeductionsRegistry(
            is_married=is_married,
            use_itemized=use_itemized,
            donations=Decimal(str(donations)),
            insurance_premiums=Decimal(str(insurance)),
            medical_maternity=Decimal(str(medical)),
            mortgage_interest=Decimal(str(mortgage)),
            savings_and_investment=Decimal(str(savings_inv)),
            educational_tuition=Decimal(str(edu_tuition)),
            pre_school_children=Decimal(str(pre_school)),
            housing_rent=Decimal(str(house_rent)),
            foreign_income=Decimal(str(amt_foreign)),
            insurance_benefits=Decimal(str(amt_insurance)),
            private_securities=Decimal(str(amt_securities)),
            has_salary_income=has_salary,
            disability_count=int(disability_cnt),
            long_term_care_count=int(ltc_cnt),
            dividend_income=Decimal(str(dividend_amt))
        )
        
        session = TaxFilingSession(
            profile=profile_instance, 
            income_entries=income_instances, 
            deductions=deductions_instance
        )
        
        # 2. Pass directly into your core computation engine
        metrics = TaxCalculator.calculate(session)
        
        # 3. Render Visual Layout Metrics Summary
        st.success("Calculation Completed!")
        
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            st.metric("Total Gross Income", f"${metrics['total_gross_income']:,} TWD")
            st.metric("Total Exemptions Allowed", f"${metrics['total_exemptions']:,} TWD")
        with res_col2:
            st.metric("Total Deductions Applied", f"${metrics['total_deductions']:,} TWD")
            if metrics['amt_supplementary_due'] > 0:
                st.metric("AMT Supplementary Tax Due", f"${metrics['amt_supplementary_due']:,} TWD", delta="AMT Triggered", delta_color="inverse")
            else:
                st.metric("AMT System Status", "Passed Safety Margin", delta="Regular Rate Applies")
        with res_col3:
            st.metric("Net Taxable Base", f"${metrics['net_taxable_income']:,} TWD")
            st.metric("Gross Tax Payable", f"${metrics['gross_tax_payable']:,} TWD")
            
            # Showcase Final Reconciliation details
            recon_amount = f"${metrics['final_reconciliation_amount']:,} TWD"
            if metrics["balance_status"] == "REFUND":
                st.metric("🎉 Final Status: REFUND", recon_amount, delta="Refund Owed to You")
            else:
                st.metric("⚠️ Final Status: BALANCE DUE", recon_amount, delta="-Payment Required", delta_color="inverse")
                
    except Exception as e:
        st.error(f"Data Schema Structure Verification Failed: {str(e)}")
        st.info(f"💡 **Automated Dividend Tax Optimization Strategy Selected:** {metrics['chosen_strategy']}")