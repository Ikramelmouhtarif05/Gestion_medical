import mysql.connector
from mysql.connector import Error
import os

def setup_database():
    """Création/initialisation de la base MySQL à partir du fichier sql2_schema.sql"""

    print("\n Initialisation de la base de données 'gestion_suivi_medical'...\n")

    # Vérifie si le fichier existe avant exécution
    sql_file = "database/sql2_schema.sql"
    if not os.path.exists(sql_file):
        print(f"❌ Fichier introuvable : {sql_file}")
        print("Place ton fichier dans /database/sql2_schema.sql ou modifie le chemin dans le script")
        return

    try:
        # Connexion MySQL (sans base au départ)
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='123456'
        )

        if connection.is_connected():
            print("✅ Connexion MySQL réussie")

            cursor = connection.cursor()

            # Lecture du SQL complet
            with open(sql_file, "r", encoding="utf-8") as f:
                sql_schema = f.read()

            print(" Fichier SQL chargé, exécution en cours...\n")

            # Exécution multi-requêtes du fichier SQL
            for result in cursor.execute(sql_schema, multi=True):
                pass  # obligatoire pour mysql.connector

            connection.commit()

            print("=============================================")
            print(" Base de données configurée avec succès !")
            print(" Nom BD : gestion_suivi_medical")
            print(" Schéma importé depuis sql2_schema.sql")
            print("=============================================\n")

            print(" Comptes par défaut disponibles (si inclus dans ton fichier .sql) :")
            print("   ➤ Élève 1 : mariedupont / password")
            print("   ➤ Élève 2 : jeanmartin2 / password")
            print("   ➤ Médecin 1 : mariedurand / password")
            print("   ➤ Médecin 2 : jeanmartin / password")
            print("\n Lancement application →  python run.py\n")

    except Error as e:
        print(f"❌ ERREUR MYSQL : {e}\n")
        print(" Aide rapide :")
        print(" - Vérifie que MySQL est démarré (service en cours)")
        print(" - Vérifie l'utilisateur / mot de passe MySQL")
        print(" - Le fichier .sql doit contenir CREATE DATABASE & USE gestion_suivi_medical")
        print(" - Exception montré ci-dessus permet de corriger rapidement")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    setup_database()
