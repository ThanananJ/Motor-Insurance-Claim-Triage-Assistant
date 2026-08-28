# Motor Insurance Claim Triage Assistant

## Presentation Script --- 7 Slides

> เป้าหมาย: ใช้เป็นบทพูดสำหรับ Presentation ประมาณ 7--10 นาที\
> หลักการ: ใน Slide แสดงเฉพาะ Key Message ส่วนรายละเอียดใช้การพูดอธิบาย

------------------------------------------------------------------------

# Slide 1 --- Business Problem & Objective

## สิ่งที่ควรมีบน Slide

**Motor Insurance Claim Triage Assistant**

### Current Problems

-   Manual Review Effort
-   Inconsistent Triage Quality
-   Delayed Risk Detection
-   Slow Customer Response

### Objective

**AI-assisted Initial Claim Triage --- Human Final Decision**

## บทพูด

โปรเจกต์นี้คือ **Motor Insurance Claim Triage Assistant** หรือระบบ AI
ที่เข้ามาช่วย Claim Officer ในการคัดกรองเคลมรถยนต์เบื้องต้น

ปัญหาของกระบวนการปัจจุบันคือ Claim Officer ต้องตรวจสอบข้อมูลหลายส่วนด้วยตัวเอง
ไม่ว่าจะเป็นรายละเอียดเหตุการณ์หรือ Claim Description, เงื่อนไข Policy,
เอกสารที่ลูกค้าส่งมา รวมถึงประวัติการเคลม

ทำให้เกิด Pain Point หลักประมาณ 4 เรื่องครับ

เรื่องแรกคือ **Manual Review Effort**
เจ้าหน้าที่ต้องใช้เวลาอ่านและตรวจข้อมูลหลายส่วนด้วยตัวเอง

เรื่องที่สองคือ **Inconsistent Triage Quality** เจ้าหน้าที่แต่ละคนอาจตีความ Policy
เอกสารที่ขาด หรือ Risk Signal แตกต่างกัน

เรื่องที่สามคือ **Delayed Risk Detection** เช่น ความผิดปกติของ Claim
หรือหลักฐานที่ไม่เพียงพอ อาจถูกตรวจพบช้า

และสุดท้ายคือ **Slow Customer Response** ถ้าข้อมูลไม่ครบ อาจต้องติดต่อลูกค้าหลายรอบ
ทำให้ Cycle Time เพิ่มขึ้น

ดังนั้น Objective ของ Solution นี้คือใช้ AI เข้ามาช่วยทำ **Initial Claim Triage
ให้เร็วและสม่ำเสมอมากขึ้น** แต่ AI จะไม่ได้เป็นคนอนุมัติหรือปฏิเสธ Claim โดย Final
Decision ยังคงเป็นหน้าที่ของ Claim Officer

------------------------------------------------------------------------

# Slide 2 --- AI Use Case & User Workflow

## สิ่งที่ควรมีบน Slide

### Input

-   Claim Description
-   Incident Date
-   Submitted Documents
-   Claim History

### AI Assistant

-   Understand & Extract Claim Facts
-   Assess Initial Coverage
-   Identify Missing Documents
-   Detect Risk Flags
-   Recommend Routing
-   Explain Reasoning

### Output

-   Claim Summary
-   Coverage Assessment
-   Missing Documents
-   Risk Flags
-   Recommended Routing
-   Reasoning
-   Confidence

**AI Recommendation → Claim Officer Review → Human Final Decision**

## บทพูด

สำหรับ Use Case หลัก ผู้ใช้งานของระบบคือ **Motor Insurance Claim Officer**

ในมุมของ User กลุ่มนี้ งานไม่ได้มีแค่การอ่าน Claim Description แต่ระหว่าง Initial
Triage ต้องตรวจหลายอย่างร่วมกัน ทั้งรายละเอียดเหตุการณ์, Submitted Documents,
Policy Conditions, Claim History รวมถึงข้อมูลที่ยัง Missing หรือ Uncertain
ก่อนพิจารณาว่าเคสควรถูก Review หรือ Route ไปขั้นตอนไหน

ดังนั้นสิ่งที่ Officer ต้องการไม่ใช่ให้ AI ตัดสินแทน แต่ให้ช่วยรวบรวมและจัดข้อมูลสำคัญ
ให้เห็นชัด ลดการไล่อ่านหลายส่วน และเปิดให้แก้สิ่งที่ AI เข้าใจผิดก่อนนำไปใช้ต่อ
แนวคิดนี้ทำให้ Prototype เลือก Structured Workflow ที่แสดง Claim Information,
AI Suggested Facts และ Triage Result อย่างเป็นขั้นตอน พร้อม Human Confirmation
ที่ชัดเจน

เจ้าหน้าที่จะส่งข้อมูล Claim เข้ามา เช่น Claim Description, วันที่เกิดเหตุ,
เอกสารที่ได้รับ และประวัติการเคลมของลูกค้า

AI Assistant จะช่วยทำงานหลัก ๆ คือ เข้าใจ Claim Description และ Extract
ข้อเท็จจริงออกมาเป็น Structured Facts จากนั้นช่วยประเมิน Coverage เบื้องต้น
ตรวจว่าเอกสารหรือข้อมูลอะไรยังขาด ตรวจ Risk Flags และแนะนำ Routing ที่เหมาะสม

ผลลัพธ์ที่ได้จะไม่ได้เป็นเพียง Free-text Response แต่จะออกมาเป็น **Structured Triage
Result** เช่น Claim Summary, Coverage Assessment, Missing Documents, Risk
Flags, Recommended Routing, Reasoning และ Confidence

หลังจากนั้น Claim Officer จะ Review และแก้ AI Suggested Facts, Confirm ข้อมูล
อย่างชัดเจน และตรวจ Triage Result ที่อ่านได้รวดเร็ว ก่อนเป็นผู้ตัดสินใจขั้นสุดท้าย

ดังนั้น AI ในระบบนี้มีบทบาทเป็น **Decision Support System ไม่ใช่ Decision Maker**

------------------------------------------------------------------------

# Slide 3 --- Solution Architecture

## สิ่งที่ควรมีบน Slide

``` text
                       Claim Officer
                             ↓
              Gradio Human-in-the-Loop UI
                    + Claim Information
                             ↓
                   Workflow Orchestrator
                             ↓
          Local LLM / Ollama — Semantic Extraction
                             ↓
                    AI Suggested Facts
                             ↓
             Structured / Pydantic Validation
                             ↓
          Human Review & Correction → Confirmation
                             ↓
                       Confirmed Facts
                             ↓
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
 Policy Grounding       Rule Engine          Risk Engine
        └────────────────────┼────────────────────┘
                             ↓
                  Triage Recommendation
                             ↓
                 Claim Officer Final Decision
```

### Design Principle

**LLM for Language Understanding + Human for Fact Verification + Policy &
Rules for Deterministic Triage + Human for Final Decision**

## บทพูด

ในแนวคิดแรก ผมตั้งใจให้ Interface เป็น **Chatbot ร่วมกับ Structured Panel**
เพราะใน Business Use Case จริง Claim Officer น่าจะส่งข้อมูลหรือสอบถามผ่าน
ภาษาธรรมชาติได้สะดวก แล้วให้ระบบช่วยวิเคราะห์ก่อนแสดงผลแบบ Structured

แต่สำหรับ Prototype รอบนี้ ผมเลือก Scope เป็น **Structured
Human-in-the-Loop UI ด้วย Gradio** ก่อน เพื่อสาธิต Workflow ตั้งแต่รับข้อมูลจนถึง
Triage Recommendation ได้ครบ ทำให้ AI Suggested Facts มองเห็นชัด เจ้าหน้าที่แก้ไข
และยืนยันได้โดยตรง ลดความกำกวมของหน้าจอแบบสนทนา และแสดง Safety Boundary
ระหว่าง AI กับ Deterministic Logic ได้ชัดเจน ส่วน Chatbot ยังเป็น Future Interface
Enhancement ได้

Architecture ปัจจุบันเริ่มจาก Claim Officer กรอก Claim Information ผ่าน Gradio
จากนั้น **Workflow Orchestrator** จะประสานลำดับการทำงาน โดย **Local LLM ผ่าน
Ollama** รับผิดชอบเฉพาะการเข้าใจความหมายของ Free Text เช่น ข้อความว่า
“Vehicle stolen from condominium parking” สามารถเสนอ Event Type เป็น theft ได้

ผลจาก LLM จะเป็นเพียง **AI Suggested Facts** ยังไม่ใช่ Business Facts ที่ระบบเชื่อถือ
ทันที จากนั้น **Pydantic Validation** จะตรวจว่าโครงสร้างและชนิดข้อมูลตรงตาม Schema
แต่ไม่ได้รับรองว่าความหมายถูกต้อง

Claim Officer จึงต้อง Review แก้ไข และกด Confirm อย่างชัดเจน จุดนี้คือ
**Human-in-the-Loop Trust Boundary** และมีเพียง **Confirmed Facts** เท่านั้นที่ส่งต่อ
ไปยัง Deterministic Triage

ในส่วน Deterministic นั้น **Policy Grounding** ให้ Exact Policy Context ที่ระบบต้องใช้
**Rule Engine** ตรวจ Required Documents, Coverage หรือ Exclusion รวมถึงกฎวันที่และ
ตัวเลขอย่างแน่นอน และ **Risk Engine** ประเมิน Risk Signals ที่รองรับ

ระบบจึงให้ผลเป็น **Triage Recommendation** ไม่ใช่คำตัดสิน Claim
ผู้ตัดสินใจสุดท้ายยังคงเป็น Claim Officer เสมอ นี่คือ Hybrid AI Architecture:
LLM เข้าใจภาษา, Human ยืนยันข้อเท็จจริง, Policy กับ Rules ทำ Triage อย่างแม่นยำ
และ Human เป็นผู้ตัดสินใจสุดท้ายครับ

------------------------------------------------------------------------

# Slide 4 --- How the AI Solution Works

## สิ่งที่ควรมีบน Slide

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Local LLM / Ollama                  Free-text understanding,
                                      extraction, summary, explanation

  Policy Grounding / RAG              Ground analysis with insurance
                                      policy

  Rule Engine                         Documents, dates, explicit rules

  Risk Engine                         Risk signals and inconsistencies

  Pydantic                            Validate structured output

  Orchestrator                        Control end-to-end workflow
  -----------------------------------------------------------------------

### Workflow

**Claim Input → Extract Facts → Policy Grounding → Rules & Risk →
Routing → Explanation → Human Review**

## บทพูด

ถ้าดูในรายละเอียดว่าแต่ละ Technique ถูกเลือกมาใช้ตรงไหน

ใน MVP เราใช้ **Ollama + Local LLM** เป็น Primary LLM Runtime
โดยใช้สำหรับงาน Semantic เป็นหลัก เช่น อ่าน Claim Description, Extract Facts,
สรุป Claim และสร้าง Explanation

เหตุผลที่เลือก Local LLM สำหรับ Prototype คือสามารถรันบนเครื่องได้ ไม่มี Paid API
Dependency และช่วยลดการส่ง Claim Information ออกไปยัง Cloud

แต่เราไม่ได้ผูก Business Logic เข้ากับ Model โดยตรง ตัว Architecture มี LLM
Provider Layer ทำให้ในอนาคตสามารถเปลี่ยนไปใช้ Cloud LLM เช่น Gemini หรือ
Provider อื่นได้ โดยไม่ต้องออกแบบ Rule Engine หรือ Routing ใหม่

สำหรับ Policy เราใช้ **Policy Grounding** เพื่อให้การวิเคราะห์อ้างอิง Policy
ที่ระบบได้รับ สำหรับ MVP ที่ Policy ยังมีขนาดเล็กสามารถใช้ Exact Policy Context
ได้ก่อน และ Architecture เตรียมไว้ให้พัฒนาเป็น RAG เมื่อ Policy Knowledge Base
มีขนาดใหญ่ขึ้น

ส่วนสิ่งที่ต้องการความแม่นยำ เช่น ตรวจ Required Documents หรือคำนวณวันที่ จะใช้
**Rule Engine** แทนการให้ LLM คำนวณ

และ Output จาก LLM จะต้องผ่าน **Pydantic Schema Validation**
ก่อนที่จะนำไปใช้ใน Workflow ต่อ เพื่อป้องกัน Output ที่ผิด Format หรือค่าที่ระบบไม่รองรับ

ดังนั้น Workflow โดยรวมคือ รับ Claim เข้ามา จากนั้น Extract Facts, Ground ด้วย
Policy, ตรวจ Rules และ Risks, กำหนด Routing Recommendation และสร้าง
Explanation ก่อนส่งให้ Human Review

------------------------------------------------------------------------

# Slide 5 --- Live Prototype Demo

## สิ่งที่ควรมีบน Slide

## Live Prototype Demo

**End-to-End Claim Triage**

``` text
Step 1
Claim Information
      ↓
Step 2
AI Suggested Facts
+ Human Review & Confirmation
      ↓
Step 3
Triage Recommendation
```

## บทพูด

ต่อไปผมจะสลับจาก Presentation ไปที่ **Gradio Prototype ที่รันอยู่จริง**
เพื่อ Demo End-to-End Claim Triage ครับ

Workflow มี 3 ขั้นตอน ขั้นแรก Claim Officer เลือก Assignment Case หรือกรอก
Claim Information เช่น Description, Claim History, Dates และ Submitted Documents

ขั้นที่สอง ระบบจะเรียก Local LLM ผ่าน Ollama เพื่อเสนอ **AI Suggested Facts**
จากนั้น Claim Officer ต้องตรวจทุกค่า แก้ไขเมื่อจำเป็น และกด Confirm อย่างชัดเจน
ก่อนที่ข้อมูลจะเข้าสู่ Deterministic Triage

ขั้นที่สาม ระบบจะแสดง Triage Recommendation พร้อม Initial Coverage Assessment,
Missing Information, Risk Signals และ Reasoning โดยผลที่เห็นเป็น Recommendation
ไม่ใช่ Final Claim Decision

ระหว่าง Demo ผมจะชี้ให้เห็นว่า AI Output ยังแก้ไขได้, Human Confirmation เป็น
ขั้นตอนบังคับ และ Claim Officer ยังคงเป็นผู้ตัดสินใจสุดท้ายครับ

------------------------------------------------------------------------

# Slide 6 --- Evaluation & Testing

## สิ่งที่ควรมีบน Slide

### Evaluation Areas

-   Claim Understanding / Semantic Fact Extraction
-   Coverage Assessment
-   Missing Document Detection
-   Risk Flag Detection
-   Routing Recommendation
-   Deterministic Reasoning / Explanation
-   Human-in-the-Loop Safety

### Actual Prototype Test Results

| Case | Scenario | Expected | Actual | Result |
|---|---|---|---|---|
| TC01 | Normal collision | Appropriate normal triage | Manual Review — unresolved information | **PARTIAL** |
| TC02 | Illegal street racing | Not Covered → Rejection Review | Not Covered → Rejection Review | **PASS** |
| TC03 | Vehicle theft | Police Report required → Manual Review | Missing Police Report → Manual Review | **PASS** |
| TC04 | Severe damage + weak evidence | Fraud Review | Fraud Review | **PASS** |
| TC05 | Late submission >30 days without reason | Manual Review | Manual Review | **PASS\*** |

\* TC05 routing is correct, but the LLM returned
`late_submission_valid_reason = unknown` instead of `false` — a known semantic
extraction limitation.

### Testing Strategy

**1. Deterministic Unit Tests**  
Documents • Dates • Exclusions • Risk • Routing • Human-review enforcement

**2. LLM + End-to-End Evaluation**  
Semantic facts • Event/exclusion/risk signals • UNKNOWN safety • Structured
facts for officer review • Integration with deterministic triage

### Key Result

**3 PASS + 1 PASS\* + 1 PARTIAL**

> Core deterministic triage behavior passed the critical Assignment scenarios,
> while testing also identified remaining LLM semantic extraction limitations.
>
> **Every recommendation requires Human Review; the Claim Officer retains final authority.**

### Design Principle

**LLM proposes semantic facts → Deterministic Logic applies Policy and routing
→ Human Claim Officer makes the final decision**

## บทพูด

หลังจาก Implementation เราทดสอบระบบทั้งในส่วน **Deterministic Logic**
และการทำงานร่วมกับ **Local LLM แบบ End-to-End** ครับ

เราใช้ Assignment Test Cases ทั้ง 5 เคส โดยตรวจตั้งแต่การเข้าใจ Claim,
Coverage Assessment, Missing Documents, Risk Signals, Routing Recommendation,
Reasoning และการบังคับใช้ Human-in-the-Loop

ผลที่ได้คือ **TC02, TC03 และ TC04 ผ่านตาม Expected Result** โดย TC02
ตรวจ Policy Exclusion จาก Illegal Racing และ Route ไป Rejection Review ได้
TC03 ตรวจพบ Police Report ที่ขาดในเคส Theft และ Route ไป Manual Review
ส่วน TC04 ตรวจ Severe Damage ร่วมกับ Weak Evidence และ Repeated Claims
แล้ว Route ไป Fraud Review ได้

สำหรับ **TC05** ระบบคำนวณ Late Submission ได้ 45 วันและ Route ไป Manual Review
ถูกต้อง แต่มีข้อจำกัดของ LLM ใน Semantic Extraction คือค่า
`late_submission_valid_reason` ยังออกเป็น `unknown` แทน `false`
จึงแสดงผลเป็น PASS พร้อม Known Limitation

ส่วน **TC01 เป็น Partial** เพราะ Claim ยังมีข้อมูลบางส่วนที่ไม่ครบ ระบบจึงเลือก
Manual Review แบบ Conservative เพื่อไม่ให้ AI ตัดสินเกินหลักฐานที่มี

Testing Strategy แบ่งเป็นสองชั้นครับ ชั้นแรกคือ **Deterministic Unit Tests**
สำหรับ Logic ที่ต้องให้ผลแน่นอนและทำซ้ำได้ เช่น Required Documents,
Date Calculation, Policy Exclusion, Risk Escalation, Routing และการบังคับ
Human Review

ชั้นที่สองคือ **LLM และ End-to-End Evaluation** เพื่อดูว่า Local LLM สามารถ
Extract Semantic Facts, ระบุ Event Type หรือ Risk Signals, รักษาค่า UNKNOWN
เมื่อข้อมูลกำกวม และส่ง Structured Facts ให้ Claim Officer ตรวจสอบก่อนทำงานร่วมกับ
Deterministic Triage ได้หรือไม่

ดังนั้นผลนี้ไม่ได้หมายถึง Accuracy 100% แต่แสดงว่า Critical Routing Rules
ทำงานในสถานการณ์สำคัญ และ Evaluation สามารถเปิดเผยข้อจำกัดด้าน Semantic
Extraction ของ LLM ได้จริง

จุดสำคัญคือ **LLM มีหน้าที่เสนอ Facts, Deterministic Logic ใช้ Policy และ
Business Rules เพื่อให้ Routing Recommendation และ Claim Officer เป็นผู้ตรวจสอบ
และตัดสินใจสุดท้ายเสมอครับ**

------------------------------------------------------------------------

# Slide 7 --- AI Risk, Governance & Production Readiness

## สิ่งที่ควรมีบน Slide

  Risk                  Mitigation
  --------------------- -------------------------------------------
  Hallucination         Policy Grounding + Rules
  Privacy               Local LLM + Synthetic Data + Minimize PII
  Prompt Injection      Treat Claim Input as Untrusted Data
  Inconsistent Output   Structured Schema Validation
  Overconfidence        Confidence + Human Review
  Explainability        Reasoning + Policy / Rule Reference
  Auditability          Log Model / Prompt / Rules / Output

### Human-in-the-Loop

**AI Recommends → Human Reviews → Human Decides**

### Future

**OCR → Real Policy RAG → Core Insurance Integration → Monitoring &
Audit**

## บทพูด

สุดท้ายคือเรื่อง AI Risk, Governance และ Production Readiness ซึ่งสำคัญมากสำหรับ
Insurance Use Case

Risk แรกคือ **Hallucination** ครับ LLM อาจตีความหรือสร้างข้อมูลที่ไม่มีอยู่จริง
เราจึงใช้ Policy Grounding และ Deterministic Rules และไม่ให้ LLM เป็น Source of
Truth สำหรับ Business Decision

เรื่อง **Privacy** ใน Assignment เราใช้ Synthetic Data และ MVP ใช้ Local LLM
เป็น Primary Path รวมถึง Minimize PII เพื่อลดการส่ง Claim Information
ออกไปภายนอกโดยไม่จำเป็น

สำหรับ **Prompt Injection** เรากำหนดให้ Claim Description ถูกมองเป็น
Untrusted Data ไม่ใช่ Instruction ที่สามารถเปลี่ยน System Behavior ได้

ส่วน **Inconsistent Output** เกิดจาก LLM อาจคืน Format หรือ Value ไม่สม่ำเสมอ
ระบบจึงใช้ Structured Schema Validation ด้วย Pydantic เพื่อตรวจ Data Type,
Required Fields และ Allowed Values ก่อนแสดงเป็น AI Suggested Facts ให้ Claim
Officer Review แต่ Pydantic ไม่ได้รับรอง Semantic Correctness จึงยังต้องใช้
Human Review

สำหรับ **Overconfidence** LLM อาจตอบอย่างมั่นใจแม้ข้อมูล Claim ยังไม่เพียงพอ
ระบบจึงใช้ค่า TRUE, FALSE และ UNKNOWN โดยถ้าหลักฐานไม่พอจะคงเป็น UNKNOWN
แทนการบังคับให้ AI เดา และมี Prototype Confidence Level เพื่อสื่อระดับความไม่แน่นอน
ซึ่งเป็น Deterministic หรือ Heuristic Indicator ไม่ใช่ Probability หรือ Confidence
Score จาก LLM และยังต้องผ่าน Human Review กับ Confirmation

ในเรื่อง **Explainability** ระบบจะแสดง Deterministic Reasoning, Missing หรือ
Unresolved Information, Risk Signals รวมถึง Policy หรือ Rule Reference
เพื่อให้ Claim Officer ตรวจสอบได้ว่า Recommendation เกิดจากเหตุผลอะไร

ส่วน **Auditability** หากไม่มี Audit Trail จะตรวจสอบย้อนหลังได้ยากว่า Recommendation
ในขณะนั้นมาจาก Model, Prompt หรือ Rule Version ใด สำหรับ Production จึงควรเก็บ
Model Version, Prompt Version, Rule Version, Confirmed Facts และ Recommendation
หรือ Output เพื่อให้ Trace ได้ โดย Full Audit Trail ส่วนนี้เป็น Future Production
Control และยังไม่ได้ Implement ใน MVP

แต่ Guardrail ที่สำคัญที่สุดคือ **Human-in-the-Loop**

AI สามารถช่วย Extract Information และสร้าง Recommendation แต่ไม่สามารถ Final
Approve, Final Reject หรือ Authorize Payment ได้

ดังนั้น Flow จะเป็น\
**AI Recommends → Human Reviews → Human Decides**

Claim Officer ยังคงเป็น Final Decision Maker

สำหรับการพัฒนาต่อใน Production สามารถเพิ่ม OCR และ Document Intelligence,
Real Policy RAG, Integration กับ Insurance Core System รวมถึง Monitoring
และ Audit ได้ในอนาคต

------------------------------------------------------------------------

# Closing Summary

## ข้อความสำหรับพูดปิด

สรุป Solution ของเราคือ **Hybrid AI-assisted Motor Insurance Claim Triage
Assistant**

เราไม่ได้ใช้ LLM ทำทุกอย่าง แต่แบ่ง Responsibility ตามจุดแข็งของแต่ละ Technique

**LLM** ใช้สำหรับเข้าใจภาษาและ Semantic Reasoning

**Policy Grounding** ใช้เพื่อให้ AI วิเคราะห์จาก Policy จริง

**Rule Engine** ใช้สำหรับ Business Logic ที่ต้องแม่นยำและทำซ้ำได้

**Risk Engine** ใช้ช่วยค้นหา Risk Signals

และ **Structured Validation** ทำให้ AI Output
สามารถนำไปใช้กับระบบต่อได้อย่างปลอดภัยมากขึ้น

สุดท้าย AI จะทำหน้าที่เป็น Decision Support ให้ Claim Officer และ **Final
Decision ยังคงเป็นของ Human**

แนวคิดหลักของ Solution นี้คือ

> **Use AI where AI is strong, use deterministic rules where precision
> matters, and keep humans accountable for the final claim decision.**

------------------------------------------------------------------------

# Q&A --- ประเด็นที่ควรเตรียมตอบ

หากกรรมการถามรายละเอียด สามารถขยายเรื่องต่อไปนี้ได้:

-   ทำไมไม่ใช้ LLM ทำทุกอย่าง?
-   ทำไมเลือก Ollama + Local LLM?
-   Local LLM ต่างจาก Cloud LLM อย่างไร?
-   RAG ใช้ตรงไหน และ MVP ใช้ RAG จริงหรือ Exact Policy Context?
-   Rule Engine ต่างจาก LLM อย่างไร?
-   Orchestrator คืออะไร?
-   Structured Output / Schema / Pydantic คืออะไร?
-   Risk Flag ต่างจาก Fraud Decision อย่างไร?
-   ถ้า LLM ใช้งานไม่ได้ ระบบทำอย่างไร?
-   ทำไม Human-in-the-Loop ถึงจำเป็น?
-   ป้องกัน Hallucination อย่างไร?
-   Prompt Injection ป้องกันอย่างไร?
-   Evaluation วัดอะไร?
-   ถ้า Policy มีจำนวนมากขึ้น Architecture จะเปลี่ยนอย่างไร?
-   ถ้าจะขึ้น Production ต้องเพิ่มอะไรบ้าง?
