# Motor Insurance Claim Triage Assistant

## AI Solution Design Summary

> เอกสารฉบับนี้สรุปปัญหาของ Assignment, แนวทางการทำงานของ Solution,
> การเลือกใช้ AI/Technique, การทำงานของ Frontend, จุดที่ต้องมี
> Human-in-the-loop และโครงสร้าง Repository
>
> เนื้อหาครอบคลุม Required Sections ของ Part 1 — AI Solution Design

------------------------------------------------------------------------

# 1. Business Problem and Pain Points

## 1.1 Business Background

บริษัทประกันรถยนต์ได้รับ Claim จำนวนมากในแต่ละวัน ปัจจุบัน Claim Officer
ต้องตรวจสอบข้อมูลหลายส่วนด้วยตนเอง เช่น

-   Claim Description
-   Policy Rules
-   Submitted Documents
-   Customer Claim History

กระบวนการ Manual Review ทำให้เกิดปัญหาหลักดังนี้

| Business Issue | ปัญหา |
|---|---|
| **Manual review effort** | Claim Officer ใช้เวลาอ่าน Claim ตรวจ Policy และตรวจเอกสารด้วยตนเอง |
| **Inconsistent triage quality** | Claim Officer แต่ละคนอาจตีความ Policy<br>(เงื่อนไขกรมธรรม์), Missing Documents<br>(เอกสารที่ขาด) และ Risk Signals<br>(สัญญาณความเสี่ยง) แตกต่างกัน |
| **Delayed risk detection** | Fraud Indicator, Exclusion หรือ Weak Evidence อาจถูกตรวจพบช้า |
| **Slow customer response** | ข้อมูลไม่ครบ ทำให้ต้องติดต่อลูกค้าหลายรอบและเพิ่ม Cycle Time |

## 1.2 ปัญหาที่ Solution ต้องการแก้

Solution นี้โฟกัส Initial Claim Triage โดยแบ่งปัญหาออกเป็น 5 กลุ่ม

### Problem 1 --- Claim

Claim Description มักเป็นข้อความ Free Text

ตัวอย่าง:

> รถลูกค้าจอดอยู่ที่ห้างแล้วถูกรถอีกคันชน

ระบบต้องเข้าใจว่าเหตุการณ์คืออะไร และแปลงเป็น Structured Facts

------------------------------------------------------------------------

### Problem 2 --- ตรวจสอบเอกสาร

ระบบต้องตรวจว่าเอกสารที่ Claim Officer ได้รับครบตาม Policy หรือไม่

ตัวอย่าง:

``` text
Claim Type (ประเภทการเคลม): Theft (รถถูกขโมย)

Submitted (เอกสารที่ส่งแล้ว):
✓ Claim Form (แบบฟอร์มเรียกร้องค่าสินไหม)
✓ Vehicle Registration (สำเนาทะเบียนรถ)

Missing (เอกสารที่ขาด):
✗ Driving License (ใบอนุญาตขับขี่)
✗ Incident Report (รายงานเหตุการณ์)
✗ Police Report (ใบแจ้งความ)
```

------------------------------------------------------------------------

### Problem 3 --- ตรวจ Coverage / Exclusion

ระบบต้องตรวจว่าเหตุการณ์:

-   มีแนวโน้ม Covered
-   อาจ Covered แต่ข้อมูลยังไม่ครบ
-   เข้า Explicit Exclusion
-   หรือยัง Cannot determine

โดยต้องใช้เฉพาะ Policy ที่ระบบได้รับเป็น Grounding

------------------------------------------------------------------------

### Problem 4 --- ตรวจ Risk Signal

ระบบช่วยหา Indicator เช่น:

- **Repeated Claims** — การเรียกร้องสินไหมซ้ำ
- **Inconsistent Story** — ข้อมูลเหตุการณ์ไม่สอดคล้องกัน
- **Severe Damage + Weak Evidence**  
  ความเสียหายรุนแรงและมีหลักฐานไม่เพียงพอ
- **Missing Evidence** — หลักฐานขาดหาย
- **Conflicting Information** — ข้อมูลขัดแย้งกัน

ระบบไม่ได้ตัดสินว่าเป็น Fraud แต่ใช้ Risk Signal เพื่อแนะนำ Fraud Review หรือ
Manual Review

------------------------------------------------------------------------

### Problem 5 --- ช่วย Routing

ระบบต้องแนะนำ Next Route:

- **Standard processing** — กระบวนการพิจารณาตามปกติ
- **Manual review** — การตรวจสอบโดยเจ้าหน้าที่
- **Fraud review** — การตรวจสอบการทุจริต
- **Rejection review** — การพิจารณาปฏิเสธเคลม

AI ไม่ใช่ Final Decision Maker

------------------------------------------------------------------------

# 2. Target Users and User Journey

## 2.1 Target User

ผู้ใช้งานหลักคือ:

**Motor Insurance Claim Officer / Claim Agent**

หน้าที่ของ AI คือช่วย Claim Officer ทำ Initial Triage ได้เร็วและสม่ำเสมอขึ้น

## 2.2 User Journey

``` mermaid
flowchart LR
    A[Claim Officer receives claim] --> B[Enter claim information]
    B --> C[AI analyzes claim]
    C --> D[AI checks policy and documents]
    D --> E[AI identifies risks]
    E --> F[AI returns structured triage result]
    F --> G[Claim Officer reviews result]
    G --> H[Human makes final decision / next action]
```

Claim Officer สามารถ:

1.  ใส่รายละเอียด Claim
2.  ส่งรายการเอกสาร
3.  ให้ AI วิเคราะห์
4.  ตอบ Follow-up Question หากข้อมูลไม่พอ
5.  ตรวจ Structured Result
6.  ตัดสินใจว่าจะดำเนินการต่ออย่างไร

------------------------------------------------------------------------

# 3. AI Use Case Definition

## 3.1 AI Assistant ทำอะไร

AI Assistant มีหน้าที่:

- **Summarize Claim** — สรุปข้อมูลเคลม
- **Understand Claim Description** — ทำความเข้าใจรายละเอียดเคลม
- **Extract Structured Facts**  
  แยกข้อเท็จจริงให้อยู่ในรูปแบบที่มีโครงสร้าง
- **Assess Initial Coverage** — ประเมินความคุ้มครองเบื้องต้น
- **Identify Missing Documents / Information**  
  ระบุเอกสารหรือข้อมูลที่ขาด
- **Identify Risk Flags** — ระบุสัญญาณความเสี่ยง
- **Recommend Routing** — แนะนำเส้นทางการดำเนินงาน
- **Explain Reasoning** — อธิบายเหตุผล
- **Indicate Confidence / Uncertainty**  
  ระบุระดับความมั่นใจหรือความไม่แน่นอน

## 3.2 Input (ข้อมูลนำเข้า)

ตัวอย่าง Input (ข้อมูลนำเข้า):

``` text
Claim ID (รหัสเคลม)
Customer (ลูกค้า)
Vehicle (รถยนต์)
Incident Date (วันที่เกิดเหตุ)
Claim Submitted Date (วันที่ยื่นเคลม)
Claim Description (รายละเอียดเคลม)
Documents Submitted (เอกสารที่ยื่นแล้ว)
Customer Claim History (ประวัติการเคลมของลูกค้า)
```

## 3.3 Output

``` json
{
  "claim_summary": "...",
  "initial_coverage_assessment": "Likely covered",
  "missing_information": [],
  "risk_flags": [],
  "recommended_routing": "Manual review",
  "reasoning": "...",
  "confidence_level": "High"
}
```

## 3.4 Decision Boundary

AI สามารถ **Recommend** ได้ แต่ไม่สามารถ:

- **Final Approve Claim** — อนุมัติเคลมขั้นสุดท้าย
- **Final Reject Claim** — ปฏิเสธเคลมขั้นสุดท้าย
- **Authorize Payment** — อนุมัติการจ่ายเงิน
- ทำ **Settlement** — ตกลงชดใช้ค่าสินไหม
- ทำ **Irreversible Business Decision**  
  การตัดสินใจทางธุรกิจที่ไม่สามารถย้อนกลับได้

Final Decision ต้องเป็นของ Human Claim Officer

------------------------------------------------------------------------

# 4. Conceptual Solution Design

แนวคิดหลักคือ **Hybrid AI Claim Triage Assistant**

ไม่ได้ให้ LLM ทำทุกอย่าง แต่เลือก Technique ให้เหมาะกับแต่ละปัญหา

``` mermaid
flowchart TD
    USER[Claim Officer] --> UI[Gradio: Chatbot + Structured Claim Panel]
    UI --> ORCH[AI / Workflow Orchestrator]

    ORCH --> LLMP[LLM Provider Layer]
    LLMP --> LC[langchain-ollama]
    LC --> LOCAL[Ollama + Local LLM - MVP Primary]
    LLMP -. Optional / Future .-> CLOUD[Gemini / Cloud LLM]
    ORCH --> RAG[RAG / Policy Grounding]
    ORCH --> RULE[Rule Engine]
    ORCH --> RISK[Risk Engine]

    RAG --> POLICY[(Policy Knowledge Base)]

    LOCAL --> RESULT[Triage Logic]
    CLOUD --> RESULT
    RULE --> RESULT
    RAG --> RESULT
    RISK --> RESULT

    RESULT --> VALIDATE[Structured Output Validator]
    VALIDATE --> UI
    UI --> HUMAN[Human Final Review]
```

หลักการ:

> **LLM ใช้กับภาษาและ Semantic Reasoning\
> RAG ใช้กับ Policy Knowledge\
> Rule Engine ใช้กับ Business Logic ที่ต้องแน่นอน\
> Risk Engine ใช้ตรวจ Risk Indicator\
> Human เป็นผู้ตัดสิน Claim ขั้นสุดท้าย**

------------------------------------------------------------------------

# 5. Technique Selection --- ใช้อะไรแก้ปัญหาส่วนไหน

| ขั้นตอน / ปัญหา | Technique | วิธีใช้งาน | เหตุผล |
|---|---|---|---|
| รับ Claim จากข้อความ | LLM | อ่าน Free-text Claim | เข้าใจ Natural Language ได้ดี |
| Extract Claim Facts | LLM + Schema | แปลงข้อความเป็น Claim Type, Event, Location ฯลฯ | Backend นำข้อมูลไปใช้ต่อได้ |
| ค้น Policy | RAG | Retrieve Policy Section ที่เกี่ยวข้อง | Ground AI ด้วย Policy จริง |
| ตรวจ Required Documents | Rule Engine | เปรียบเทียบ Required กับ Submitted | เป็น Deterministic Rule |
| คำนวณ Late Submission | Python / Rule Engine | คำนวณ Incident Date → Submitted Date | ต้องแม่นยำ จึงไม่ควรให้ LLM คำนวณ |
| ตรวจ Explicit Exclusion | Rule Engine + Policy | ใช้ Exclusion ตาม Policy ฉบับเต็ม | ลด Hallucination และคงเงื่อนไขครบถ้วน |
| ตรวจ Repeated Claims | Risk Engine | ตรวจ Claim History | ใช้เป็น Risk Signal ไม่ใช่ Policy Threshold |
| ตรวจ Story Inconsistency | LLM | Semantic Comparison | Rule ปกติตรวจความหมายได้ยาก |
| สร้าง Claim Summary | LLM | Summarization | เป็นจุดแข็งของ Generative AI |
| สร้าง Explanation | Grounded LLM | อธิบาย Facts + Policy + Rules | Claim Officer ต้องเข้าใจเหตุผล |
| Validate Output | Pydantic / Schema | ตรวจ JSON และค่าที่อนุญาต | ทำให้ Output ใช้งานต่อได้ |
| Final Decision | Human | Claim Officer Review | Governance / Accountability |

------------------------------------------------------------------------

# 6. LLM

## 6.1 หน้าที่

LLM ใช้สำหรับ:

- **Natural Language Understanding** — การทำความเข้าใจภาษาธรรมชาติ
- **Claim Classification / Extraction**  
  การจำแนกประเภทและการสกัดข้อมูลเคลม
- **Summarization** — การสรุปข้อมูล
- **Semantic Risk Analysis** — การวิเคราะห์ความเสี่ยงเชิงความหมาย
- **Human-readable Explanation** — คำอธิบายที่มนุษย์เข้าใจได้

ตัวอย่าง:

``` text
Input:
รถถูกขโมยจากลานจอดคอนโด

LLM Extraction:
claim_type = theft
event_type = vehicle_theft
location = condominium_parking
```

## 6.2 สิ่งที่ไม่ควรให้ LLM ทำ

ไม่ควรใช้ LLM เป็นตัวหลักในการ:

-   คำนวณจำนวนวัน
- ตรวจ **Required Document** (เอกสารที่จำเป็น) แบบตรงไปตรงมา
- **Exact Date / Numeric Calculation**  
  การคำนวณวันที่หรือตัวเลขอย่างแม่นยำ
- **Final Approval / Rejection** — การอนุมัติหรือปฏิเสธขั้นสุดท้าย
- สร้าง **Policy Rule** (กฎของกรมธรรม์) เอง

## 6.3 Model Strategy

MVP ไม่จำเป็นต้อง Train Model ใหม่

MVP เลือก **Ollama + Local LLM** เช่น Qwen เป็น Primary LLM Runtime เพราะไม่มี
Paid API Dependency หรือ API Key สำหรับ Local Inference, Claim Information
สามารถอยู่บนเครื่องระหว่างประมวลผล และ Prototype สามารถทำงานโดยไม่พึ่ง Cloud LLM
Service จึงเหมาะกับการสาธิต Privacy-aware AI Architecture ในขอบเขต Assignment

Local Model ใช้เฉพาะงาน Semantic ได้แก่ Free-text Understanding, Structured Fact
Extraction, Semantic Inconsistency/Risk Signals, Claim Summary และ Grounded
Explanation โดยไม่แทนที่ Document Rules, Date Calculation, Explicit Policy
Application หรือ Deterministic Routing

LLM Layer ยังคงเป็น Provider-independent Abstraction โดยมี Gemini API หรือ Cloud
LLM อื่นเป็น Optional / Future Provider เพื่อลด Vendor Lock-in และรองรับการเพิ่ม
หรือเปลี่ยน Provider ภายหลังโดยไม่ออกแบบ Business Logic ใหม่

MVP วาง `langchain-ollama` เป็น Integration Layer สำหรับการสื่อสารระหว่าง
Application กับ Ollama เท่านั้น ไม่ได้ควบคุม Workflow และไม่รับผิดชอบ Policy,
Rule Engine, Risk Engine หรือ Routing

``` text
Application
    ↓
LLM Provider Layer
    ├── langchain-ollama → Ollama + Local LLM   ← MVP Primary
    └── Gemini / Cloud LLM   ← Optional / Future
```

Local LLM ไม่ได้ดีกว่า Cloud LLM ในทุกกรณี คุณภาพและ Latency ขึ้นกับ Model และ
ทรัพยากร CPU, GPU และ RAM ของเครื่องที่ใช้

หาก Ollama/Model ใช้งานไม่ได้, Inference ล้มเหลว หรือ Structured Output ไม่ผ่าน
Validation ระบบต้องไม่สร้าง Semantic Facts ขึ้นเอง ต้องคง UNKNOWN, ทำ
Deterministic Checks ที่ยังทำได้, แจ้งว่า AI Analysis ไม่สมบูรณ์ และรักษา Human
Review โดย Detailed Retry/Fallback Behavior อยู่ในขั้น Implementation

Pydantic เป็น Structured Validation Boundary ก่อน AI-generated Facts เข้าสู่
Deterministic Core ส่วน `uv` ใช้จัดการ Python Environment, Dependencies,
Lockfile และ Project Execution เท่านั้น ไม่ใช่ส่วนหนึ่งของ AI Inference Flow

------------------------------------------------------------------------

# 7. RAG / Policy Grounding

## 7.1 หน้าที่

RAG ทำหน้าที่ค้น Policy ที่เกี่ยวข้องกับ Claim ก่อนส่ง Context ให้ LLM

ตัวอย่าง:

``` text
Claim:
Vehicle stolen from condominium

        ↓

RAG Query:
theft claim coverage required documents

        ↓

Retrieved Policy:
- Theft is a covered event
- Police report is required for theft
```

LLM จึง Reason จาก Policy ที่ Retrieve มา แทนการใช้ความรู้ทั่วไปของตัวเอง

## 7.2 เหตุผลที่เลือก

-   ลด Hallucination
-   Policy Update ได้โดยไม่ Train LLM ใหม่
-   รองรับ Policy จำนวนมากในอนาคต
-   สามารถแสดง Source Reference ได้
-   เหมาะกับ Company-specific Knowledge

## 7.3 MVP

Policy ของ Assignment ยังมีขนาดเล็ก

Prototype แรกสามารถใช้:

``` text
Simple Policy Context Injection
```

ก่อน และเตรียม Interface สำหรับ Lightweight RAG

Target Architecture ยังคงเป็น Retrieval-based Grounding

------------------------------------------------------------------------

# 8. Rule Engine

Rule Engine ใช้กับ Logic ที่มีคำตอบแน่นอน

## 8.1 Document Rules

Rule Engine เปรียบเทียบเอกสารที่ส่งมากับ Required Documents ตาม Policy
โดยตรง ครอบคลุมเอกสารสำหรับทุก Claim และเอกสารเพิ่มเติมตามประเภทเหตุการณ์

ชื่อเอกสารสามารถ Normalize ภายในระบบเพื่อรองรับรูปแบบการเขียนที่ต่างกันได้
แต่ทุก Requirement ต้อง Trace กลับไปยังข้อความ Policy ต้นฉบับ โดยเฉพาะ
Third-party contact information and evidence ซึ่งต้องคงความหมายครบถ้วน

## 8.2 Date Rule

ระบบคำนวณระยะเวลาระหว่าง Incident Date และ Claim Submitted Date ด้วย
Deterministic Code หากเกิน 30 วันต้องพิจารณาเงื่อนไข Policy ฉบับเต็มว่า
"Claim filed more than 30 days after the incident without valid reason"
จึงไม่สามารถสรุปจากจำนวนวันเพียงอย่างเดียวได้

## 8.3 Explicit Exclusion Rules

Explicit Exclusion ต้องอ้างอิง Policy Source of Truth โดยไม่ย่อ เพิ่ม
หรือตีความเป็นกฎใหม่ เมื่อมีข้อมูลที่ยืนยันว่า Exclusion ใช้ได้อย่างชัดเจน
ระบบจึงแนะนำ Rejection Review เพื่อให้ Claim Officer ตรวจสอบต่อ

Rule Engine (กลไกประมวลผลกฎ) ทำให้ผลลัพธ์:

- **Predictable** — คาดการณ์ได้
- **Reproducible** — ทำซ้ำแล้วได้ผลลัพธ์เดิม
- **Testable** — ทดสอบได้
- **Auditable** — ตรวจสอบย้อนหลังได้

------------------------------------------------------------------------

# 9. Risk Engine

Risk Engine ใช้ Hybrid Rules + LLM

## Rule-based Risk

Risk Engine ตรวจสัญญาณที่ Policy ระบุ เช่น suspicious pattern, repeated claims
และ severe damage with weak evidence โดยไม่สร้าง Numeric Policy Threshold
เพิ่มเติม จำนวน Claim ใน Test Case เป็นข้อมูลประกอบการประเมิน ไม่ใช่เกณฑ์ตัวเลข
ที่กำหนดโดย Policy

## LLM-assisted Risk

ใช้ตรวจ:

-   Story ขัดแย้งกัน
-   Claim Description ไม่สอดคล้องกับ Evidence Description
-   Information Conflict

Risk Flag ไม่ใช่ Fraud Decision

------------------------------------------------------------------------

# 10. AI / Workflow Orchestrator

Orchestrator เป็น Backend Component ที่ควบคุมลำดับการทำงาน

``` mermaid
flowchart TD
    A[Receive Claim] --> B[Validate Input]
    B --> C[LLM Extract Claim Facts]
    C --> D[Validate Structured Facts]
    D --> E[Calculate Deterministic Values]
    E --> F[Retrieve Policy]
    F --> G[Check Documents]
    G --> H[Check Exclusions]
    H --> I[Detect Risk Flags]
    I --> J[Determine Routing]
    J --> K[LLM Generate Summary + Explanation]
    K --> L[Validate Output]
    L --> M[Return to Claim Officer]
```

สำหรับ Assignment นี้เลือก **Deterministic Workflow Orchestration** แทน
Fully Autonomous Agent เพราะ:

-   Test ง่ายกว่า
-   Debug ง่ายกว่า
-   Explain ง่ายกว่า
-   Control Business Rule ได้ดีกว่า
-   Complexity เหมาะกับ Prototype

------------------------------------------------------------------------

# 11. Frontend --- Gradio Chatbot + Structured Claim Panel

MVP เลือก Gradio เป็น Frontend สำหรับ Chatbot, Structured Claim Input และ
Structured Result Panel โดย UI เป็น Interaction Layer และไม่มีอำนาจเปลี่ยนผลจาก
Deterministic Workflow

## 11.1 Chatbot

Gradio Chatbot เป็น Interaction Layer

Claim Officer สามารถพิมพ์:

> รถลูกค้าถูกขโมยจากคอนโด มี Claim Form กับทะเบียนรถ

AI สามารถถามต่อ:

> ยังไม่พบ Incident Date และ Police Report กรุณาระบุข้อมูลเพิ่มเติม

## 11.2 Structured Claim Panel

Chatbot ไม่ควรเป็น UI เพียงอย่างเดียว

ด้านข้างควรแสดง:

``` text
Claim Type (ประเภทการเคลม)
Theft (รถถูกขโมย)

Coverage (ความคุ้มครอง)
Likely Covered (มีแนวโน้มได้รับความคุ้มครอง)

Documents (เอกสาร)
✓ Claim Form (แบบฟอร์มเรียกร้องค่าสินไหม)
✓ Vehicle Registration (สำเนาทะเบียนรถ)
✗ Driving License (ใบอนุญาตขับขี่)
✗ Incident Report (รายงานเหตุการณ์)
✗ Police Report (ใบแจ้งความ)

Risk Flags (สัญญาณความเสี่ยง)
None (ไม่มี)

Recommended Routing (เส้นทางการดำเนินงานที่แนะนำ)
Manual Review (การตรวจสอบโดยเจ้าหน้าที่)

Confidence (ระดับความมั่นใจ)
High (สูง)
```

ข้อดี:

-   Claim Officer ไม่ต้องย้อนอ่านข้อความ
-   เห็น Current Claim State
-   ตรวจ AI Extraction ได้
-   Explainability ดีขึ้น
-   Human สามารถตรวจหรือแก้ข้อมูลได้

------------------------------------------------------------------------

# 12. Human-in-the-Loop

Flow จบที่ Human

``` mermaid
flowchart LR
    AI[AI Triage Result] --> OFFICER[Claim Officer Review]
    OFFICER --> DECISION[Human Final Decision]
```

AI ส่งให้ Claim Officer:

1. **Claim Summary** — สรุปข้อมูลเคลม
2. **Initial Coverage Assessment** — การประเมินความคุ้มครองเบื้องต้น
3. **Missing Information / Documents** — ข้อมูลหรือเอกสารที่ขาด
4. **Risk Flags** — สัญญาณความเสี่ยง
5. **Recommended Routing** — เส้นทางการดำเนินงานที่แนะนำ
6. **Reasoning** — เหตุผลประกอบ
7. **Confidence** — ระดับความมั่นใจ
8. **Policy / Rule Reference** — เอกสารอ้างอิงกรมธรรม์หรือกฎ (เมื่อมี)

Claim Officer ต้อง:

-   ตรวจว่า AI เข้าใจ Claim ถูกต้องหรือไม่
-   ตรวจ Missing Information
-   ตรวจ Policy / Reasoning
-   พิจารณา Risk Flags
-   ขอข้อมูลเพิ่มถ้าจำเป็น
-   เลือก Final Route / Final Business Decision

AI จึงเป็น **Decision Support System** ไม่ใช่ Decision Maker

------------------------------------------------------------------------

# 13. Data Requirements

ข้อมูลที่ Prototype ต้องใช้:

## Claim Data (ข้อมูลเคลม)

``` text
Claim ID (รหัสเคลม)
Customer (ลูกค้า)
Vehicle (รถยนต์)
Incident Date (วันที่เกิดเหตุ)
Claim Submitted Date (วันที่ยื่นเคลม)
Claim Description (รายละเอียดเคลม)
Documents Submitted (เอกสารที่ยื่นแล้ว)
Customer Claim History (ประวัติการเคลมของลูกค้า)
```

## Policy Data (ข้อมูลกรมธรรม์)

``` text
Covered Events (เหตุการณ์ที่ได้รับความคุ้มครอง)
Exclusions (ข้อยกเว้นความคุ้มครอง)
Required Documents (เอกสารที่จำเป็น)
Routing Guidance (แนวทางการกำหนดเส้นทางดำเนินงาน)
```

## Future Data (ข้อมูลในอนาคต)

Production (ระบบที่ใช้งานจริง) อาจต้องเพิ่ม:

- **Real Policy Documents** — เอกสารกรมธรรม์จริง
- **Claim History Database** — ฐานข้อมูลประวัติการเคลม
- **Document Metadata** — ข้อมูลกำกับเอกสาร
- **OCR Results** — ผลลัพธ์จากการอ่านข้อความในเอกสาร
- **Fraud Investigation Outcomes** — ผลการตรวจสอบการทุจริต

Assignment (งานที่ได้รับมอบหมาย) ใช้ Synthetic Data (ข้อมูลสังเคราะห์) เท่านั้น

------------------------------------------------------------------------

# 14. Prompting / RAG / Workflow Design

Prompt Design แบ่ง Context และ Responsibility ออกเป็น 5 ส่วน เพื่อให้ LLM
ทำงานภายในขอบเขตที่ชัดเจนและเชื่อมต่อกับ Deterministic Workflow ได้อย่างปลอดภัย

1.  **System Role and Decision Boundary** — กำหนดให้ LLM เป็น Assistant สำหรับ
    Initial Claim Triage มีหน้าที่เข้าใจข้อมูล Extract Facts สรุป และช่วยอธิบาย
    แต่ไม่ทำ Final Claim Decision การประเมินตาม Rule และ Routing ยังเป็นหน้าที่ของ
    Deterministic Engine ส่วน Claim Officer เป็นผู้ตัดสินใจสุดท้าย

2.  **Exact Policy Context** — ใส่ Motor Insurance Policy Rules ที่ได้รับเป็น
    Grounding Context เพื่อให้ LLM ใช้ Policy ของ Assignment แทนการพึ่ง General
    Model Knowledge เพียงอย่างเดียว สำหรับ MVP Policy มีขนาดเล็กจึงใช้ Exact
    Policy Context ได้โดยตรง และสามารถพัฒนา Retrieval Layer เป็น RAG เมื่อ Policy
    Knowledge Base มีขนาดใหญ่ขึ้น

3.  **Claim Context as Untrusted Data** — Treat Claim Description เป็น Input Data
    ไม่ใช่ Instruction เพื่อเป็น Guardrail เบื้องต้นต่อ Prompt Injection และป้องกัน
    ไม่ให้คำสั่งที่อยู่ภายใน Claim เปลี่ยน Intended System Behavior

4.  **Task Instructions** — จำกัด LLM ให้ทำงานด้าน Semantic เช่น เข้าใจ Free Text,
    Extract Relevant Facts, ระบุ Uncertainty และสนับสนุน Summary/Explanation
    LLM ไม่คำนวณ Deterministic Policy Conditions หรือเลือก Final Routing และเมื่อ
    ข้อมูลไม่เพียงพอต้องคงความไม่แน่นอนไว้แทนการเดา

5.  **Structured Output Contract** — จำกัด Output ให้อยู่ใน Structured Format
    ที่กำหนดและ Validate ก่อนส่งเข้า Deterministic Workflow ทำให้ผลจาก LLM
    Predictable, Testable และปลอดภัยต่อการใช้ร่วมกับ Rule Engine มากขึ้น

Prompt Design อยู่ใน Workflow ดังนี้:

``` text
Claim Input
    ↓
Prompt + Exact Policy Grounding
    ↓
LLM Fact Extraction
    ↓
Structured Output Validation
    ↓
Rule Engine + Risk Engine
    ↓
Triage Recommendation
    ↓
Human Claim Officer
```

เอกสารนี้อธิบาย Prompt Design ในระดับ Solution ส่วน Detailed Guardrails,
Input/Output Behavior และ Uncertainty Handling อยู่ใน `prompts/prompt-design.md`
และ Actual Prototype Prompt Template อยู่ใน `prompts/triage-system-prompt.md`

------------------------------------------------------------------------

# 15. Evaluation Method

> วิธีการประเมินผล

ควรทดสอบ Test Cases (กรณีทดสอบ) ทั้ง 5

ตรวจ:

- **Claim Understanding** — ความเข้าใจข้อมูลเคลม
- **Coverage Assessment** — การประเมินความคุ้มครอง
- **Missing Documents** — เอกสารที่ขาด
- **Risk Flags** — สัญญาณความเสี่ยง
- **Routing** — เส้นทางการดำเนินงาน
- **Reasoning** — เหตุผลประกอบ
- **Confidence** — ระดับความมั่นใจ

Test Result (ผลการทดสอบ):

| Case<br>(กรณีทดสอบ) | Expected<br>(ผลที่คาดหวัง) | Actual<br>(ผลที่เกิดขึ้นจริง) | Result<br>(ผลลัพธ์) | Notes<br>(หมายเหตุ) |
|---|---|---|---|---|

Deterministic Rules (กฎที่ให้ผลลัพธ์แน่นอน) ควรมี Unit Tests (การทดสอบหน่วยย่อย)
แยกจาก LLM Tests (การทดสอบ LLM) เพื่อให้ตรวจสอบ Policy Application
(การประยุกต์ใช้กรมธรรม์) และความสม่ำเสมอของ Routing (เส้นทางการดำเนินงาน)
ได้อย่างชัดเจน

------------------------------------------------------------------------

# 16. Risks and Mitigation

> ความเสี่ยงและแนวทางลดความเสี่ยง

| Risk | Mitigation |
|---|---|
| **Hallucination**<br>การสร้างข้อมูลที่ไม่มีแหล่งอ้างอิง | **Policy Grounding + Rules + Strict Prompt**<br>ยึดโยงกับกรมธรรม์ ใช้กฎ และกำหนด Prompt อย่างเคร่งครัด |
| **Incorrect Policy Retrieval**<br>ดึงกรมธรรม์ไม่ถูกต้อง | **Source Reference + Retrieval Testing**<br>แสดงแหล่งอ้างอิงและทดสอบการค้นคืนข้อมูล |
| **Missing Information**<br>ข้อมูลไม่ครบถ้วน | **Ask Follow-up / Cannot Determine**<br>ถามข้อมูลเพิ่มเติม หรือระบุว่าไม่สามารถตัดสินได้ |
| **Privacy**<br>ความเป็นส่วนตัว | **Synthetic Data + Minimize PII Logging**<br>ใช้ข้อมูลสังเคราะห์และลดการบันทึกข้อมูลส่วนบุคคล |
| **Prompt Injection**<br>การแทรกคำสั่งโจมตี Prompt | **Treat Claim as Data + Input Isolation**<br>ถือข้อมูลเคลมเป็นข้อมูลเท่านั้นและแยกข้อมูลนำเข้า |
| **Inconsistent LLM Output**<br>ผลลัพธ์จาก LLM ไม่สม่ำเสมอ | **Structured Schema Validation**<br>ตรวจสอบผลลัพธ์ด้วยโครงสร้างข้อมูลที่กำหนด |
| **Overconfidence**<br>ความมั่นใจสูงเกินไป | **Confidence + Human Review**<br>แสดงระดับความมั่นใจและให้มนุษย์ตรวจสอบ |
| **Lack of Explainability**<br>ขาดความสามารถในการอธิบาย | **Show Reasoning, Rules, Policy Reference**<br>แสดงเหตุผล กฎ และแหล่งอ้างอิงกรมธรรม์ |
| **Auditability**<br>ตรวจสอบย้อนหลังได้ | **Log Prompt Version, Model, Rules, Output**<br>บันทึกเวอร์ชัน Prompt โมเดล กฎ และผลลัพธ์ |
| **Local Inference Performance**<br>ความเร็วขึ้นกับ CPU/GPU/RAM | **Select Model to Match Hardware**<br>เลือกขนาดโมเดลให้เหมาะกับทรัพยากรของเครื่อง |
| **Local Model Capability**<br>โมเดลขนาดเล็กอาจมี Semantic Accuracy ต่ำกว่า Cloud Model ขนาดใหญ่ | **Evaluation + Provider Abstraction**<br>ประเมินคุณภาพและสามารถเปลี่ยนไปใช้ Cloud Provider ได้เมื่อจำเป็น |

------------------------------------------------------------------------

# 17. MVP Scope and Roadmap

> ขอบเขตผลิตภัณฑ์ขั้นต่ำและแผนพัฒนา

## MVP

> ผลิตภัณฑ์ขั้นต่ำที่ใช้งานได้

ทำ:

- **Chat UI** — ส่วนติดต่อผู้ใช้แบบสนทนา
- **Gradio Frontend** — Chatbot, Structured Claim Input และ Structured Result Panel
- **Structured Claim Panel** — แผงข้อมูลเคลมแบบมีโครงสร้าง
- **LLM Claim Understanding** — การทำความเข้าใจข้อมูลเคลมด้วย LLM
- **Ollama + Local LLM Primary Path** — Prototype สามารถรัน Semantic AI บนเครื่องโดยไม่ต้องใช้ Paid Cloud API เป็นเส้นทางหลัก
- **Policy Grounding** — การยึดโยงข้อมูลกับกรมธรรม์
- **Rule Engine** — กลไกประมวลผลกฎ
- **Risk Flags** — สัญญาณความเสี่ยง
- **Routing Recommendation** — คำแนะนำเส้นทางการดำเนินงาน
- **Structured Output** — ผลลัพธ์แบบมีโครงสร้าง
- **Human Review** — การตรวจสอบโดยมนุษย์
- **Test Cases** — กรณีทดสอบ

Exact Policy Grounding และ Deterministic Business Rules แยกจาก LLM Provider
ดังนั้นการเปลี่ยนระหว่าง Local และ Cloud LLM ไม่เปลี่ยน Policy Logic หรือ Routing

ไม่ทำ:

- **Final Claim Approval** — การอนุมัติเคลมขั้นสุดท้าย
- **Payment Calculation** — การคำนวณยอดชำระ
- **Core Insurance Integration** — การเชื่อมต่อระบบประกันภัยหลัก
- **Production Fraud Model** — โมเดลตรวจจับการทุจริตสำหรับระบบจริง
- **Automatic Customer Communication** — การสื่อสารกับลูกค้าโดยอัตโนมัติ
- **Enterprise Deployment** — การติดตั้งใช้งานระดับองค์กร
- **Real Document Forgery Detection** — การตรวจจับการปลอมแปลงเอกสารจริง

## Future

> แผนพัฒนาในอนาคต

### Phase 2 — Document Intelligence

> ระยะที่ 2 — ระบบวิเคราะห์เอกสารอัจฉริยะ

- **OCR** — การอ่านข้อความจากภาพเอกสาร
- **Document Classification** — การจำแนกประเภทเอกสาร
- **Data Extraction** — การสกัดข้อมูล
- **Cross-document Validation** — การตรวจสอบความสอดคล้องระหว่างเอกสาร

### Phase 3 — Fraud Intelligence

> ระยะที่ 3 — ระบบวิเคราะห์การทุจริตอัจฉริยะ

- **Historical Claim Analytics** — การวิเคราะห์ประวัติการเคลม
- **Fraud Scoring** — การให้คะแนนความเสี่ยงด้านการทุจริต
- **Anomaly Detection** — การตรวจจับความผิดปกติ
- **Document Authenticity** — การตรวจสอบความถูกต้องแท้จริงของเอกสาร

### Phase 4 — Productionization

> ระยะที่ 4 — การเตรียมระบบสำหรับใช้งานจริง

- **Insurance Core Integration** — การเชื่อมต่อระบบประกันภัยหลัก
- **Authentication / Authorization** — การยืนยันตัวตนและการกำหนดสิทธิ์
- **Monitoring** — การติดตามสถานะระบบ
- **Audit** — การตรวจสอบย้อนหลัง
- **Prompt / Model Versioning** — การจัดการเวอร์ชัน Prompt และโมเดล
- **Cost / Latency Optimization** — การปรับต้นทุนและเวลาตอบสนองให้เหมาะสม

------------------------------------------------------------------------

# 18. Repository Structure

Repository แยกตาม Responsibility หลักเพื่อไม่ให้ UI, AI และ Business Rules
ผูกติดกัน:

- **Application / User Interface**  
  แอปพลิเคชันและส่วนติดต่อผู้ใช้
- **Policy Source / Test Data**  
  แหล่งข้อมูลกรมธรรม์และข้อมูลทดสอบ
- **LLM / Policy Grounding**  
  การยึดโยง LLM กับข้อมูลกรมธรรม์
- **Deterministic Rules / Workflow Orchestration**  
  กฎที่ให้ผลลัพธ์แน่นอนและการควบคุมลำดับขั้นตอนการทำงาน
- **Tests / Evaluation Results**  
  การทดสอบและผลการประเมิน
- **Solution Design / Prompt Design / Prototype Constraints**  
  การออกแบบโซลูชัน การออกแบบ Prompt และข้อจำกัดของต้นแบบ

โครงสร้างนี้ช่วยให้ Policy และ Deterministic Logic ตรวจสอบได้อย่างอิสระจาก
LLM พร้อมรองรับการเปลี่ยน Model หรือ UI โดยไม่กระทบ Decision Boundary

------------------------------------------------------------------------

# 19. Mapping กับ Required Sections ของ Assignment

  Required Section                    อยู่ในเอกสารส่วน
  ----------------------------------- --------------------
  Business problem and pain points    Section 1
  Target users and user journey       Section 2
  AI use case definition              Section 3
  Conceptual solution design          Section 4
  Technical architecture design       Sections 4, 10, 11
  Model and technique selection       Sections 5--9
  Data requirements                   Section 13
  Prompting / RAG / workflow design   Sections 7, 10, 14
  Evaluation method                   Section 15
  Risks and mitigation                Section 16
  MVP scope and roadmap               Section 17

ดังนั้น Design นี้ครอบคลุม Required Sections ของ Part 1 --- AI Solution Design
ครบทั้งหมด

------------------------------------------------------------------------

# 20. Solution Summary

Solution ที่เลือกคือ:

## Hybrid AI-assisted Motor Insurance Claim Triage Assistant

``` text
Claim Officer
      ↓
Gradio: Chatbot + Structured Claim Panel
      ↓
Backend / Workflow Orchestrator
      ↓
┌──────────┬──────────┬─────────────┐
│   LLM    │   RAG    │ Rule Engine │
└──────────┴──────────┴─────────────┘
             +
        Risk Engine
             ↓
     Structured Result
             ↓
       Claim Officer
             ↓
     Human Final Decision
```

### LLM

ใช้สำหรับ:

> เข้าใจ Claim → Extract Facts → Summarize → Explain → Semantic Risk

MVP ใช้ Ollama + Local LLM เป็น Primary Provider และคง Gemini / Cloud LLM เป็น
Optional / Future Provider ผ่าน Provider-independent Layer

### RAG

ใช้สำหรับ:

> ค้น Policy → Ground Coverage Reasoning → แสดง Policy Reference

### Rule Engine

ใช้สำหรับ:

> Required Documents → Date Calculation → Explicit Exclusions →
> Deterministic Business Rules

### Risk Engine

ใช้สำหรับ:

> Claim History Pattern → Weak Evidence → Semantic Inconsistency

### Structured Output Validator

ใช้สำหรับ:

> ทำให้ AI Output อยู่ใน Schema ที่ Backend/UI ใช้งานได้

### Chatbot + Structured Panel

ใช้สำหรับ:

> ให้ Claim Officer คุยกับ AI ได้ง่าย พร้อมเห็น Claim State
> และผลวิเคราะห์แบบมีโครงสร้าง

### Human

ทำหน้าที่:

> Review AI Recommendation → ตรวจข้อมูล/เหตุผล → ขอข้อมูลเพิ่มเมื่อจำเป็น →
> ตัดสินใจขั้นสุดท้าย

------------------------------------------------------------------------

> **Design Principle:**\
> ใช้ AI ในสิ่งที่ AI ทำได้ดี ใช้ deterministic rules ในสิ่งที่ต้องแม่นยำ และรักษา
> Human Decision Boundary สำหรับการตัดสิน Claim ขั้นสุดท้าย
