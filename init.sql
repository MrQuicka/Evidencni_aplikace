-- Inicializační SQL skript pro databázi docházky
-- Tento skript se spustí pouze pokud databáze neobsahuje žádné tabulky

-- Nastavení character setu
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Vytvoření databáze (pokud neexistuje)
CREATE DATABASE IF NOT EXISTS dochazka CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dochazka;

-- Poznámka: Tabulky jsou vytvářeny automaticky pomocí Flask-SQLAlchemy
-- Tento soubor slouží především pro zajištění správného nastavení databáze
-- a případné budoucí inicializační skripty

-- Vytvoření tabulky users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vytvoření tabulky projects
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    user_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vytvoření tabulky log_entry
CREATE TABLE IF NOT EXISTS log_entry (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME NULL,
    pause_start DATETIME NULL,
    pause_end DATETIME NULL,
    note TEXT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_project_id (project_id),
    INDEX idx_user_id (user_id),
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Poznámka: Admin uživatel (username: admin, password: admin) 
-- je vytvářen automaticky při prvním spuštění aplikace
