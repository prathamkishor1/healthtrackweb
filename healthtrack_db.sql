CREATE DATABASE healthtrack_db;

USE healthtrack_db;

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255)
);

CREATE TABLE health_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    date DATE,
    temperature FLOAT,
    blood_pressure VARCHAR(20),
    spo2 INT,
    sugar_level INT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
