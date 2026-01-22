CREATE DATABASE gestion_suivi_medical;
USE gestion_suivi_medical;



-- Table Elève
CREATE TABLE Eleve (
  NE INT PRIMARY KEY,
  nom_eleve VARCHAR(50) NOT NULL,
  prénom_eleve VARCHAR(50) NOT NULL,
  date_naissance DATE NOT NULL,
  sexe ENUM('féminin','masculin') NOT NULL,
  classe_niveau_d_étude VARCHAR(50),
  tele VARCHAR(20)
);

-- Table Médecin
CREATE TABLE medecin (
  CIN VARCHAR(20) PRIMARY KEY,
  nom_medecin VARCHAR(50) NOT NULL,
  prénom_medecin VARCHAR(50) NOT NULL,
  Tele_medecin VARCHAR(20),
  date_naissance DATE NOT NULL,
  adresse_email VARCHAR(100) UNIQUE NOT NULL,
  adresse_hebergement VARCHAR(100),
  spécialiste VARCHAR(20) DEFAULT 'généraliste',
  ville_hebergement VARCHAR(20) 
);

-- Table Dossier
CREATE TABLE Dossier (
  id_dossier INT PRIMARY KEY AUTO_INCREMENT,
  mld_chr TEXT,
  groupe_sanguin VARCHAR(10),
  date_creation DATE,
  NE INT,
  FOREIGN KEY (NE) REFERENCES Eleve(NE) ON DELETE CASCADE
);

-- Table Consultation
CREATE TABLE consultation (
  id_consultation INT PRIMARY KEY AUTO_INCREMENT,
  date_consult DATE,
  analyses TEXT,
  état_malade TEXT,
  CIN VARCHAR(20),
  id_dossier INT,
  NE INT,
  FOREIGN KEY (CIN) REFERENCES medecin(CIN),
  FOREIGN KEY (id_dossier) REFERENCES Dossier(id_dossier),
  FOREIGN KEY (NE) REFERENCES Eleve(NE)
);

-- Table Ordonnance
CREATE TABLE ordonnance (
  id_ordonnance INT PRIMARY KEY AUTO_INCREMENT,
  médicaments TEXT,
  date_ DATE,
  durée VARCHAR(50),
  id_consultation INT,
  NE INT,
  CIN VARCHAR(20),
  id_dossier INT,
  FOREIGN KEY (id_consultation) REFERENCES consultation(id_consultation),
  FOREIGN KEY (NE) REFERENCES Eleve(NE),
  FOREIGN KEY (CIN) REFERENCES medecin(CIN),
  FOREIGN KEY (id_dossier) REFERENCES Dossier(id_dossier)
);

-- Table Rendez-vous
CREATE TABLE rendez_vous (
  id_rend INT PRIMARY KEY AUTO_INCREMENT,
  date_rend DATE NOT NULL,
  heure_rend TIME NOT NULL,
  statut ENUM('En_attente','Terminee') DEFAULT 'En_attente',
  type_rend VARCHAR(50),
  unique(date_rend,heure_rend),
  id_consultation INT,
  CIN VARCHAR(20),
  NE INT,
  FOREIGN KEY (id_consultation) REFERENCES consultation(id_consultation),
  FOREIGN KEY (CIN) REFERENCES medecin(CIN),
  FOREIGN KEY (NE) REFERENCES Eleve(NE)
);

-- Table Users (pour l'authentification)
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,  -- Stockage hashé des mots de passe
  role ENUM('medecin', 'eleve') NOT NULL,
  CIN VARCHAR(20),
  NE INT,
  FOREIGN KEY (CIN) REFERENCES medecin(CIN),
  FOREIGN KEY (NE) REFERENCES Eleve(NE)
);
