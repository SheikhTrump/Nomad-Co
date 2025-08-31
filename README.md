# NomadNest - Co-living Space Booking Platform

NomadNest is a full-stack web application built with **Flask** and **MongoDB** that provides a platform for digital nomads and travelers to find and book co-living spaces across Bangladesh.
It features distinct roles for **travelers**, **hosts**, and **administrators**, each with a dedicated dashboard and unique functionalities.

---

## Core Features

### 👤 Traveler

* **Browse & Filter**: Search for spaces with filters for location, price, and amenities.
* **Booking System**: Secure booking for specific dates.
* **User Profiles**: Manage personal details, preferences, and emergency contacts.
* **Favorites**: Save favorite spaces for future trips.
* **Reviews**: Leave ratings and feedback for stays.
* **Booking History**: View and cancel past/upcoming bookings.

### 🏠 Host

* **Space Management**: Create, edit, and manage property listings.
* **Host Verification**: Submit documents for admin approval before listing spaces.
* **Payout Dashboard**: Track total earnings and detailed payout breakdowns.

### 🛠️ Admin

* **Analytics Dashboard**: Visual reports (via Chart.js) on revenue, user growth, popular locations, and top hosts.
* **Host Verification Management**: Review and approve pending host verifications.

---

## Tech Stack

**Backend**

* Python 3
* Flask
* MongoDB
* Pymongo
* Werkzeug (password hashing)

**Frontend**

* HTML5
* Tailwind CSS
* JavaScript
* Chart.js
* Jinja2

**Environment**

* python-dotenv for environment variables

---

## 📂 Project Structure

```
nomadnest/
│── app.py              # Main Flask app entry point
│── requirements.txt    # Project dependencies
│── models/             # Database models and logic
│── routes/             # Flask Blueprints (routes and views)
│── templates/          # Jinja2 HTML templates
│── static/             # CSS, JS, and uploaded images
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites

* Python 3.8+
* MongoDB (local or MongoDB Atlas)

### 2. Clone Repository

```bash
git clone https://github.com/your-username/nomadnest.git
cd nomadnest
```

### 3. Create Virtual Environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your_super_secret_key_here
MONGO_URI=mongodb://localhost:27017/nomadnest
```

### 6. Run the Application

```bash
python app.py
```

App will run at: [http://127.0.0.1:5001](http://127.0.0.1:5001)

---

## 💡 Usage

* **First Run**: Visiting `/spaces` auto-populates the database with **26 sample spaces** and host users.
* **Sign Up**: Choose to register as **Traveler** or **Host**.
* **Admin Access**: Use credentials:

  * Email: `admin@nomad.com`
  * Password: `Black`

---

## 📌 License

This project is for educational and development purposes.

---
