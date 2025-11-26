# AgriRentX
AgriRentX is a full-stack Django-based web application designed to streamline the rental of agricultural equipment for farmers and providers. The platform ensures authenticated bookings, transparent transactions, real-time availability tracking, and organized management of equipment rentals.

## 🚀 Features

### 🔐 User Authentication
- Secure login & registration system  
- Role-based access for Farmers and Equipment Providers  
- Profile management for all users  

### 📦 Equipment Management
- Add, update, and delete equipment listings  
- Upload equipment images  
- Track availability status in real-time  
- View equipment details and specifications  

### 📝 Booking System
- Request rental bookings  
- Automated booking validation  
- Track current, past, and upcoming rentals  
- Prevent double-booking with availability checks  

### 💳 Payment & Charges
- Transparent cost calculation  
- Penalty and late-return charge system  
- Secure tracking of payments  

### 🗂️ Admin Dashboard
- Manage all users, equipment, and transactions  

## 🛠️ Tech Stack

| Layer | Technologies |
|------|--------------|
| Backend | Django, Python |
| Database | SQLite3 |
| Frontend | HTML, CSS, JavaScript |
| Environment | Virtualenv, pip |
| Media Files | Django Media Storage |

## 📂 Project Structure
```
AgriRentX/
│── manage.py
│── db.sqlite3
│── requirements.txt
│── media/
│── agri.sqlite3
│── new.sqlite3
│
└── AgriRentX/
    │── settings.py
    │── urls.py
    │── wsgi.py
    │── asgi.py
└── main/
    │── models.py
    │── views.py
    │── forms.py
    │── urls.py
    │── templates/
    │── static/
```

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone <your-repo-url>
cd AgriRentX
```

### 2️⃣ Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate       # Windows
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Apply Migrations
```bash
python manage.py migrate
```

### 5️⃣ Run the Server
```bash
python manage.py runserver
```

### 6️⃣ Access Application
```
http://127.0.0.1:8000/
```

### 7️⃣ 📸 Media Handling 



## 🔮 Future Enhancements
- Online payment gateway integration  
- Live SMS/Email notifications  
- Predictive analytics for equipment demand  
- GPS-based equipment tracking  
- Mobile app version  

## 🤝 Contributing
Pull requests are welcome!  

## 📄 License
MIT License
