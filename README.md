# 🚦 Road Safety Violation Detector  

An AI-powered system that detects traffic violations, identifies number plates, and generates automated e-challans with QR-based payment support.

---

## ✅ Build Status  

| Status | State |
|--------|--------|
| Build | Complete – Demo Ready |
| Web App | Running on Flask (port 5000) |
| Database | Pre-loaded with demo data |
| PDF System | Working with image evidence |

---

## 🔥 Core Features  

### 🎯 AI Violation Detection  

- Helmet & triple-riding detection (YOLOv8)  
- Automatic License Plate Recognition (EasyOCR)  
- Real-time evidence capture & analysis  
- Fallback CV methods when ML unavailable  

---

### 💳 Payment & Challan System  

- Auto-generated PDF e-challans with images  
- UPI QR-based payment workflow  
- Email receipt with payment confirmation  
- Repeat offense fine escalation  

---

### 📍 Location & Tracking  

- GPS coordinate storage  
- Interactive map view for violation locations  
- Location-based filtering and search  

---

### 🌐 Modern Web Portal  

- Search violations by vehicle number  
- View history, status, images, and PDFs  
- Responsive UI (Bootstrap 5)  

---

## 🚗 Demo Vehicles to Test  

| Vehicle No. | Status |
|-------------|--------|
| MH01AB1234 | 2 Violations (₹500 + ₹1000) |
| KA05CD5678 | 1 Violation (₹500) |
| TN07EF9012 | Triple Riding (₹500) |
| DL03GH3456 | No Helmet (₹500) |

---

## 🧠 Tech Stack  

| Layer | Tech |
|-------|------|
| Backend | Flask, Python, SQLite, SQLAlchemy |
| AI/ML | YOLOv8, EasyOCR, OpenCV |
| UI | Bootstrap 5, Leaflet Maps, JavaScript |
| Reporting | FPDF (PDF Generator) |

---

## 📂 Project Structure  

```
road_safety_violation_detector/
│
├── website/            # Web app (Flask)
├── services/           # AI, OCR, PDF & business logic
├── db/                 # Models & migrations
├── scripts/            # Setup & demo scripts
└── storage/            # Evidence images & PDFs
```



---


## 📄 API & Routes  

| Route | Description |
|-------|-------------|
| \`/\` | Home search page |
| \`/search\` | Search violations |
| \`/vehicle/<no>\` | View all violations |
| \`/violation/<id>\` | View details + evidence |
| \`/violation/<id>/pdf\` | Download e-challan PDF |

---

## 💰 Fine Rules  

\`\`\`python
NO_HELMET = 500
TRIPLE_RIDING = 500
REPEAT_MULTIPLIER = 2
\`\`\`

---

## 🌍 Custom YOLOv8 (Optional)  

Supports Indonesian traffic dataset with classes:

- Helm  
- Pengendara  
- PlatNomor  
- TanpaHelm  

Custom model auto-loads if available at:

\`\`\`
models/yolov8_custom_indonesian.pt
\`\`\`

---

## 🧪 Quick Test  

\`\`\`bash
python scripts/run_quick_demo.py
\`\`\`

---

## 🔐 Security  

- Input validation & sanitization  
- Safe file serving  
- Protected DB operations  

---

## 📌 Notes  

- Educational/demo use only  
- Add real payment gateway & production-grade security before deployment
---

## 👨‍💻 Author  

**Gunasai**  
B.Tech Final Year Student  
AI & ML Enthusiast  

📧 Email: ganumulapally@gmail.com  
🔗 LinkedIn: [Gunasai Anumulapally](https://www.linkedin.com/in/gunasai-anumulapally-8204b3251)
---



