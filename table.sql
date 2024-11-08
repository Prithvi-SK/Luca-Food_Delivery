CREATE DATABASE myapp;

USE myapp;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    phone_number VARCHAR(15)
);

-- Modify the admins table
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    phone_number VARCHAR(15),
    restaurant_name VARCHAR(100) NOT NULL,
    restaurant_location VARCHAR(100) NOT NULL,
    restaurant_description VARCHAR(200),
    restaurant_category VARCHAR(50)
);

-- Create the restaurants table
CREATE TABLE restaurants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT,
    restaurant_name VARCHAR(100) NOT NULL UNIQUE,
    restaurant_location VARCHAR(100) NOT NULL,
    restaurant_description VARCHAR(200),
    restaurant_category VARCHAR(50),
    FOREIGN KEY (admin_id) REFERENCES admins(id)
);
