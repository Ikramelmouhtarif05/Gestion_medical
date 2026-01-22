from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
import hashlib
from datetime import datetime, date
from config import Config
app = Flask(__name__)
app.config.from_object(Config)

# Configuration de la base de données 
def get_db_connection():
    try:
        return pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Erreur de connexion à la base de données: {e}")
        return None

# Fonctions utilitaires
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def is_eleve_logged_in():
    return 'eleve_id' in session

def is_medecin_logged_in():
    return 'medecin_id' in session

# Routes principales
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/espace_eleve')
def espace_eleve():
    return render_template('eleve/eleve_login.html')

@app.route('/espace_medecin')
def espace_medecin():
    return render_template('medecin/medecin_login.html')

# Routes pour les élèves 
@app.route('/eleve/signup', methods=['GET', 'POST'])
def eleve_signup():
    if request.method == 'POST':
        ne = request.form['ne']                
        nom = request.form['nom']
        prenom = request.form['prenom']
        date_naissance = request.form['date_naissance']
        sexe = request.form['sexe']
        classe = request.form['classe']
        telephone = request.form['telephone']
        username = request.form['username']
        password = request.form['password']
        groupe_sanguin= request.form['groupe_sanguin']
        hashed_password = hash_password(password)

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()

                cursor.execute("""
                    INSERT INTO Eleve (NE, nom_eleve, prénom_eleve, date_naissance, sexe, classe_niveau_d_étude, tele)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (ne, nom, prenom, date_naissance, sexe, classe, telephone))
                connection.commit()

                # Création dossier
                cursor.execute("INSERT INTO Dossier (date_creation, NE) VALUES (CURDATE(), %s)", (ne,))
                connection.commit()

                # Création utilisateur
                cursor.execute("""
                    INSERT INTO users (username, password, role, NE)
                    VALUES (%s, %s, 'eleve', %s)
                """, (username, hashed_password, ne))
                connection.commit()

                flash('Inscription réussie !', 'success')
                return redirect(url_for('espace_eleve'))

            except Exception as e:
                flash('Erreur : ' + str(e), 'error')
                return redirect(url_for('eleve_signup'))

            finally:
                cursor.close()
                connection.close()

    return render_template('eleve/eleve_signup_sql2.html')


@app.route('/eleve/login', methods=['GET', 'POST'])
def eleve_login():
    if request.method == 'POST':
        identifiant = request.form['username']  
        password = request.form['password']
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            
            cursor.execute("""
                SELECT u.*, e.NE, e.nom_eleve, e.prénom_eleve 
                FROM users u 
                JOIN Eleve e ON u.NE = e.NE 
                WHERE (u.username = %s OR u.NE = %s) AND u.role = 'eleve'
            """, (identifiant, identifiant))
            
            user_data = cursor.fetchone()
            cursor.close(); connection.close()
            
            #  Vérification du mot de passe
            if user_data and verify_password(password, user_data['password']):
                session['role'] = 'eleve'
                session['eleve_id'] = user_data['NE']
                session['eleve_nom'] = user_data['nom_eleve']
                session['eleve_prenom'] = user_data['prénom_eleve']
                session['username'] = user_data['username']

                flash("Connexion réussie !", "success")
                return redirect(url_for('eleve_dashboard'))
            else:
                flash("Identifiant (Username / NE) ou mot de passe incorrect.", "error")
                return redirect(url_for('eleve_login'))
        else:
            flash("Erreur de connexion à la base de données.", "error")
            return redirect(url_for('eleve_login'))
    
    return render_template('eleve/eleve_login.html')


@app.route('/eleve/dashboard')
def eleve_dashboard():
    if not is_eleve_logged_in():
        return redirect(url_for('eleve_login'))

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(pymysql.cursors.DictCursor)   
        cursor.execute("""
        UPDATE rendez_vous 
        SET statut = 'Terminee'
        WHERE statut='En_attente'
        AND CONCAT(date_rend,' ',heure_rend) < NOW()
        AND id_rend > 0;

        """)
        connection.commit()
        # Info élève
        cursor.execute("SELECT * FROM Eleve WHERE NE = %s", (session['eleve_id'],))
        eleve = cursor.fetchone()

        #  RDV à venir
        cursor.execute("""
            SELECT r.id_rend, r.date_rend, r.heure_rend, r.type_rend, r.statut,
                   m.nom_medecin, m.prénom_medecin, m.spécialiste
            FROM rendez_vous r
            JOIN medecin m ON r.CIN = m.CIN
            WHERE r.NE = %s
            AND r.statut = 'En_attente'
            AND CONCAT(r.date_rend,' ',r.heure_rend) >= NOW()
            ORDER BY r.date_rend ASC, r.heure_rend ASC
        """, (session['eleve_id'],))
        rdv_avenir = cursor.fetchall()

        #  RDV du jour
        cursor.execute("""
            SELECT r.*, m.nom_medecin, m.prénom_medecin
            FROM rendez_vous r
            JOIN medecin m ON r.CIN = m.CIN
            WHERE r.NE = %s
            AND r.date_rend = CURDATE()
            ORDER BY r.heure_rend ASC
        """, (session['eleve_id'],))
        rdv_jour = cursor.fetchall()

        #  Historique
        cursor.execute("""
            SELECT c.*, m.nom_medecin, m.prénom_medecin
            FROM consultation c
            JOIN medecin m ON c.CIN = m.CIN
            WHERE c.NE = %s
            ORDER BY c.date_consult DESC
        """, (session['eleve_id'],))
        historique = cursor.fetchall()

        #  Dossier médical
        cursor.execute("SELECT * FROM Dossier WHERE NE = %s", (session['eleve_id'],))
        dossier = cursor.fetchone()

        cursor.close()
        connection.close()

        return render_template('eleve/dashboard_sql2.html',
                              eleve=eleve, rdv_avenir=rdv_avenir,
                              rdv_jour=rdv_jour, historique=historique,
                              dossier=dossier)

    flash("Erreur de connexion à la base", "error")
    return redirect(url_for('eleve_login'))




@app.route('/eleve/prendre_rendez_vous', methods=['GET', 'POST'])
def eleve_prendre_rendez_vous():
    if 'eleve_id' not in session:
        flash("Veuillez vous connecter", "error")
        return redirect(url_for('eleve_login'))

    id_eleve = session['eleve_id']   
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # Mise à jour auto des rdv passés
        cursor.execute("""
        UPDATE rendez_vous 
        SET statut = 'Terminee'
        WHERE statut='En_attente'
        AND CONCAT(date_rend,' ',heure_rend) < NOW()
        AND id_rend > 0;
        """)
        connection.commit()
        if request.method == 'GET':
            cursor.execute("SELECT CIN, nom_medecin, prénom_medecin, spécialiste FROM medecin")
            medecins = cursor.fetchall()

            if not medecins:
                flash("Aucun médecin enregistré ⚠", "error")
                return redirect(url_for('eleve_dashboard'))

            return render_template("eleve/prendre_rendez_vous_sql2.html", medecins=medecins)

        date_rend  = request.form.get('date_rend')
        heure_rend = request.form.get('heure_rend')
        type_rend  = request.form.get('type_rend')
        cin_medecin = request.form.get('cin_medecin')

        if not all([date_rend, heure_rend, type_rend, cin_medecin]):
            flash("Tous les champs sont obligatoires ⚠", "error")
            return redirect(url_for('eleve_prendre_rendez_vous'))

        # Pas dans le passé
        if datetime.strptime(f"{date_rend} {heure_rend}", "%Y-%m-%d %H:%M") < datetime.now():
            flash("Impossible de réserver dans le passé ❌", "error")
            return redirect(url_for('eleve_prendre_rendez_vous'))

        # la disponibilité du rendez-vous
        cursor.execute("""
            SELECT 1 FROM rendez_vous 
            WHERE date_rend=%s AND heure_rend=%s AND CIN=%s
        """, (date_rend, heure_rend, cin_medecin))

        if cursor.fetchone():
            flash("❌ Ce créneau est déjà réservé !", "error")
            return redirect(url_for('eleve_prendre_rendez_vous'))

        #  créer RDV
        cursor.execute("""
            INSERT INTO rendez_vous(date_rend,heure_rend,type_rend,CIN,NE,statut)
            VALUES (%s,%s,%s,%s,%s,'En_attente')
        """,(date_rend,heure_rend,type_rend,cin_medecin,id_eleve))
        id_rdv = cursor.lastrowid

        #  vérifier dossier ou créer
        cursor.execute("SELECT id_dossier FROM dossier WHERE NE=%s",(id_eleve,))
        doss = cursor.fetchone()

        if not doss:
            cursor.execute("INSERT INTO dossier(NE,date_creation) VALUES(%s,CURDATE())",(id_eleve,))
            connection.commit()
            id_dossier = cursor.lastrowid   #  dossier créé
        else:
            id_dossier = doss['id_dossier'] #  dossier récupéré

        #  créer consultation avec dossier
        cursor.execute("""
            INSERT INTO consultation(date_consult,CIN,NE,id_dossier)
            VALUES (%s,%s,%s,%s)
        """,(date_rend,cin_medecin,id_eleve,id_dossier))
        id_consult = cursor.lastrowid

        
        cursor.execute("""
            UPDATE rendez_vous 
            SET id_consultation=%s 
            WHERE id_rend=%s
        """,(id_consult,id_rdv))

        connection.commit()

        flash("🟢✔ Rendez-vous enregistré et transmis au médecin", "success")
        return redirect(url_for('eleve_prendre_rendez_vous'))

    except Exception as e:
        return f"Erreur : {e}"

    finally:
        cursor.close()
        connection.close()


   


@app.route('/eleve/dossier_medical')
def eleve_dossier_medical():
    if not is_eleve_logged_in():
        return redirect(url_for('eleve_login'))
    
    connection = get_db_connection()
    if not connection:
        flash('Erreur de connexion à la base de données.', 'error')
        return redirect(url_for('eleve_dashboard'))

    cursor = connection.cursor()

    cursor.execute("""
        SELECT d.*, o.médicaments, o.date_ AS date_ordonnance, o.durée
        FROM Dossier d
        LEFT JOIN consultation c ON d.NE = c.NE
        LEFT JOIN ordonnance o ON c.id_consultation = o.id_consultation
        WHERE d.NE = %s
        ORDER BY o.date_ DESC
    """, (session['eleve_id'],))

    dossier_data = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('eleve/dossier_medical_sql2.html', dossier_data=dossier_data)
@app.route('/eleve/ordonnances')
def eleve_ordonnances():
    if not is_eleve_logged_in():
        return redirect(url_for('eleve_login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT o.*, c.date_consult, m.nom_medecin, m.prénom_medecin
            FROM ordonnance o
            JOIN consultation c ON o.id_consultation = c.id_consultation
            JOIN medecin m ON c.CIN = m.CIN
            WHERE o.NE = %s
            ORDER BY o.date_ DESC
        """, (session['eleve_id'],))
        ordonnances = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return render_template('eleve/ordonnances.html', ordonnances=ordonnances)
    else:
        flash('Erreur de connexion à la base de données.', 'error')
        return redirect(url_for('eleve_dashboard'))
from werkzeug.security import generate_password_hash

@app.route('/eleve/modifier', methods=['GET', 'POST'])
def eleve_modifier_info():
    # Vérifier connexion élève
    if 'eleve_id' not in session:
        flash("Veuillez vous connecter", "error")
        return redirect(url_for('eleve_login'))

    connection = get_db_connection()
    if not connection:
        flash("Erreur de connexion à la base de données", "error")
        return redirect(url_for('eleve_dashboard'))

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:

            # ====== FORMULAIRE ENVOYÉ ======
            if request.method == "POST":
                nom = request.form.get("nom")
                prenom = request.form.get("prenom")
                classe_niveau_d_étude = request.form.get("classe_niveau_d_étude")  # ⚠ bon nom
                telephone = request.form.get("telephone")
                date_naissance = request.form.get("date_naissance")

                password = request.form.get("password")
                new_password_hash = generate_password_hash(password) if password else None

                # modifier table eleve
                cursor.execute("""
                    UPDATE eleve
                    SET nom_eleve=%s,
                        prénom_eleve=%s,
                        tele=%s,
                        date_naissance=%s,
                        classe_niveau_d_étude=%s
                    WHERE NE=%s
                """, (nom, prenom, telephone, date_naissance, classe_niveau_d_étude, session['eleve_id']))


            # afficher infos 
                cursor.execute("""
                SELECT e.*
                FROM eleve e 
                WHERE e.NE=%s
            """, (session['eleve_id'],))
            
            eleve = cursor.fetchone()
            return render_template("eleve/modifier_info.html", eleve=eleve)

    except Exception as e:
        flash(f"Erreur lors de la modification : {str(e)}", "error")
        return redirect(url_for('eleve_dashboard'))

    finally:
        connection.close()






@app.route('/eleve/ordonnance/<int:id>')
def imprimer_ordonnance(id):
    if not is_eleve_logged_in():
        return redirect(url_for('eleve_login'))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT o.*, c.date_consult, m.nom_medecin, m.prénom_medecin
        FROM ordonnance o
        JOIN consultation c ON o.id_consultation = c.id_consultation
        JOIN medecin m ON c.CIN = m.CIN
        WHERE o.id_ordonnance = %s AND o.NE = %s
    """, (id, session['eleve_id']))
    ordonnance = cursor.fetchone()
    cursor.close(); connection.close()

    return render_template('eleve/impression_ordonnance.html', ordonnance=ordonnance)


@app.route('/medecin/signup', methods=['GET', 'POST'])
def medecin_signup():
    if request.method == 'POST':
        cin = request.form['cin'].strip().upper()
        nom = request.form['nom'].strip()
        prenom = request.form['prenom'].strip()
        date_naissance = request.form['date_naissance']
        email = request.form['email'].strip()
        tel = request.form.get('telephone', '').strip() or None
        ville = request.form['ville'].strip()
        adresse = request.form['adresse'].strip()
        specialiste = request.form.get('specialiste', 'généraliste')
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if password != confirm:
            flash("Les mots de passe ne correspondent pas !", "error")
            return redirect(url_for('medecin_signup'))

        hashed = hash_password(password)

        conn = get_db_connection()
        if not conn:
            flash("Erreur de connexion BD", "error")
            return redirect(url_for('medecin_signup'))

        try:
            cursor = conn.cursor()

            cursor.execute("SELECT CIN FROM medecin WHERE CIN=%s", (cin,))
            if cursor.fetchone():
                flash("CIN déjà utilisé !", "error")
                return redirect(url_for('medecin_signup'))

            cursor.execute("""
                INSERT INTO medecin (CIN, nom_medecin, prénom_medecin, Tele_medecin, date_naissance,
                adresse_email, adresse_hebergement, spécialiste, ville_hebergement)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (cin, nom, prenom, tel, date_naissance, email, adresse, specialiste, ville))

            cursor.execute("""
                INSERT INTO users (username,password,role,CIN) VALUES (%s,%s,'medecin',%s)
            """,(cin, hashed, cin))

            conn.commit()
            flash("Inscription réussie, connectez-vous.", "success")
            return redirect(url_for('medecin_login'))

        except Exception as e:
            flash(f"Erreur : {e}", "error")
        finally:
            cursor.close(); conn.close()

    return render_template('medecin/medecin_signup_sql2.html')


@app.route('/medecin/login', methods=['GET', 'POST'])
def medecin_login():   
    if request.method == 'POST':
        identifiant = request.form['username'].strip()
        password = request.form['password']
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(pymysql.cursors.DictCursor)  # récup dict

        
            cursor.execute("""
                SELECT 
                u.*,
                m.CIN,
                m.nom_medecin,
                m.prénom_medecin,
                m.adresse_email AS email,
                m.Tele_medecin AS telephone,
                m.spécialiste AS specialite,
                m.adresse_hebergement AS adresse
                FROM users u
                JOIN medecin m ON u.CIN = m.CIN
                WHERE (u.username = %s OR u.CIN = %s)
                AND u.role = 'medecin'
            """, (identifiant, identifiant))

            user_data = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if user_data and verify_password(password, user_data['password']):
                session['role'] = 'medecin'
                session['medecin_id'] = user_data['CIN']
                session['medecin_nom'] = user_data['nom_medecin']
                session['medecin_prenom'] = user_data['prénom_medecin']
                session['username'] = user_data['username']

                flash("Connexion réussie !", "success")
                return redirect(url_for('medecin_dashboard'))

            else:
                flash("Identifiant (Username / CIN) ou mot de passe incorrect.", "error")
                return redirect(url_for('medecin_login'))
        else:
            flash("Erreur de connexion à la base de données.", "error")
            return redirect(url_for('medecin_login'))
    
    return render_template('medecin/medecin_login.html')

# Dashboard Médecin

from datetime import date

@app.route('/medecin/dashboard')
def medecin_dashboard():
    if 'medecin_id' not in session:
        flash('Veuillez vous connecter', 'error')
        return redirect(url_for('medecin_login'))

    cin = session['medecin_id']
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        UPDATE rendez_vous 
        SET statut = 'Terminee'
        WHERE statut='En_attente'
        AND CONCAT(date_rend,' ',heure_rend) < NOW()
        AND id_rend > 0;

        """)
    conn.commit()
    
    #   Infos médecin
  
    cursor.execute("SELECT * FROM medecin WHERE CIN=%s", (cin,))
    medecin = cursor.fetchone()

    
    #   Rendez-vous aujourd'hui
    
    cursor.execute("""
    SELECT r.*, e.nom_eleve, e.prénom_eleve, e.tele
    FROM rendez_vous r
    JOIN eleve e ON r.NE = e.NE
    WHERE r.CIN=%s AND DATE(r.date_rend) = CURDATE()
    ORDER BY r.heure_rend
    """, (cin,))
    rdv_jour = cursor.fetchall()

    
    #   Tous les rendez-vous à venir
    
    cursor.execute("""
    SELECT r.id_rend, r.date_rend, r.heure_rend, r.type_rend, r.statut,
           e.prénom_eleve, e.nom_eleve, e.tele
    FROM rendez_vous r
    JOIN Eleve e ON r.NE = e.NE
    WHERE r.statut = 'En_attente'
    AND CONCAT(r.date_rend,' ',r.heure_rend) >= NOW()
    ORDER BY r.date_rend ASC, r.heure_rend ASC
    """)
    rdv_prochains = cursor.fetchall()


   
    #   Consultations futures

    cursor.execute("""
    SELECT c.*, e.nom_eleve, e.prénom_eleve, rv.type_rend
    FROM consultation c
    JOIN eleve e ON c.NE = e.NE
    LEFT JOIN rendez_vous rv ON rv.id_consultation = c.id_consultation
    WHERE c.CIN=%s AND c.date_consult > CURDATE()
    ORDER BY c.date_consult ASC
    """, (cin,))
    consultations = cursor.fetchall()

    conn.close()

    return render_template(
        'medecin/medecin_dashboard.html',
        medecin=medecin,
        rdv_jour=rdv_jour,
        rdv_prochains=rdv_prochains,   
        consultations=consultations,
        today=date.today()
    )


@app.route('/consultation/<int:id_consultation>', methods=['GET'])
def medecin_consultation(id_consultation):
    if not is_medecin_logged_in():
        flash('Veuillez vous connecter', 'error')
        return redirect(url_for('medecin_login'))

    conn = get_db_connection()
    if not conn:
        flash('Erreur de connexion à la base de données', 'error')
        return redirect(url_for('medecin_dashboard'))

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT c.*, d.id_dossier, d.mld_chr, d.groupe_sanguin,
            e.nom_eleve, e.prénom_eleve, e.date_naissance, e.tele
            FROM consultation c
            LEFT JOIN Dossier d ON c.id_dossier = d.id_dossier
            JOIN Eleve e ON c.NE = e.NE
            WHERE c.id_consultation=%s AND c.CIN=%s
            """, (id_consultation, session['medecin_id']))

            consultation = cursor.fetchone()

        if not consultation:
            flash('Consultation introuvable', 'error')
            return redirect(url_for('medecin_dashboard'))

        return render_template('medecin/consultation_sql2.html', consultation=consultation)
    except Exception as e:
        flash(f"Erreur lors du chargement de la consultation: {str(e)}", 'error')
        return redirect(url_for('medecin_dashboard'))
    finally:
        conn.close()

@app.route('/medecin/consultation/create/<int:ne>')
def creer_consultation(ne):
    if not is_medecin_logged_in():
        flash("Veuillez vous connecter", "error")
        return redirect(url_for('medecin_login'))

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Vérifier si consultation existe déjà
    cur.execute("SELECT id_consultation, id_dossier FROM consultation WHERE NE=%s AND CIN=%s",
                (ne, session['medecin_id']))
    exist = cur.fetchone()

    # Vérifier si dossier existe ou le créer
    cur.execute("SELECT id_dossier FROM Dossier WHERE NE=%s", (ne,))
    doss = cur.fetchone()

    if not doss:
        cur.execute("INSERT INTO Dossier (NE, date_creation) VALUES (%s, CURDATE())", (ne,))
        conn.commit()
        id_dossier = cur.lastrowid
    else:
        id_dossier = doss['id_dossier']

    # Si consultation existe mais sans dossier → mise à jour
    if exist and exist['id_dossier'] is None:
        cur.execute("UPDATE consultation SET id_dossier=%s WHERE id_consultation=%s",
                    (id_dossier, exist['id_consultation']))
        conn.commit()
        id_consultation = exist['id_consultation']

    # Sinon, si aucune consultation → création
    elif not exist:
        cur.execute("""
            INSERT INTO consultation (NE, CIN, date_consult, id_dossier)
            VALUES (%s, %s, CURDATE(), %s)
        """, (ne, session['medecin_id'], id_dossier))
        conn.commit()
        id_consultation = cur.lastrowid

    else:
        # consultation existe déjà avec dossier
        id_consultation = exist['id_consultation']

    conn.close()
    return redirect(url_for('medecin_consultation', id_consultation=id_consultation))




@app.route('/medecin_enregistrer_consultation', methods=['POST'])
def medecin_enregistrer_consultation():
    if not is_medecin_logged_in():
        flash('Veuillez vous connecter', 'error')
        return redirect(url_for('medecin_login'))

    id_consultation = request.form['id_consultation']
    analyses = request.form.get('analyses', '').strip()
    etat_malade = request.form.get('etat_malade', '').strip()
    medicaments = request.form.get('médicaments', '').strip()
    duree = request.form.get('duree', '').strip()

    conn = get_db_connection()
    if not conn:
        flash('Erreur de connexion à la base de données', 'error')
        return redirect(url_for('medecin_dashboard'))
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            
            #  Mise à jour consultation
            cursor.execute("""
                UPDATE consultation
                SET analyses=%s, état_malade=%s
                WHERE id_consultation=%s
            """, (analyses, etat_malade, id_consultation))

            #  Si une ordonnance existe → insertion
            if medicaments or duree:
                cursor.execute("SELECT NE, id_dossier FROM consultation WHERE id_consultation=%s", (id_consultation,))
                consult = cursor.fetchone()

                if consult:
                    cursor.execute("""
                        INSERT INTO ordonnance (médicaments, durée, id_consultation, NE, CIN, id_dossier, date_)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (medicaments, duree, id_consultation, consult['NE'],
                          session['medecin_id'], consult['id_dossier'], datetime.now().date()))

        conn.commit()
        flash('Consultation et ordonnance enregistrées avec succès! ✔', 'success')

    except Exception as e:
        flash(f"Erreur lors de l'enregistrement: {str(e)}", 'error')

    finally:
        conn.close()

    #  retour vers la page consultation
    return redirect(url_for('medecin_consultation', id_consultation=id_consultation))

@app.route('/medecin/recherche', methods=['GET','POST'])
def medecin_recherche():
    if not is_medecin_logged_in():
        return redirect(url_for('medecin_login'))

    eleve = None
    if request.method == 'POST':
        ne = request.form['NE']

        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute("SELECT * FROM Eleve WHERE NE=%s", (ne,))
                    eleve = cursor.fetchone()
            except Exception as e:
                flash(f"Erreur lors de la recherche: {str(e)}", 'error')
            finally:
                conn.close()

        if not eleve:
            flash("Élève introuvable", "error")

    return render_template('medecin/recherche_eleve.html', eleve=eleve)
@app.route('/medecin_ajouter_rendez_vous', methods=['GET', 'POST'])
def medecin_ajouter_rendez_vous():
    if not is_medecin_logged_in():
        return redirect(url_for('medecin_login'))

    cin = session['medecin_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        UPDATE rendez_vous 
        SET statut = 'Terminee'
        WHERE statut='En_attente'
        AND CONCAT(date_rend,' ',heure_rend) < NOW()
        AND id_rend > 0;
        """)
        conn.commit()

        if request.method == 'GET':
            cursor.execute("SELECT NE, prénom_eleve, nom_eleve FROM Eleve")
            return render_template('medecin/ajouter_rendez_vous.html', eleves=cursor.fetchall())

        id_eleve = request.form['id_eleve']
        date_rdv = request.form['date_rdv']
        heure_rdv = request.form['heure_rdv']
        type_rend = request.form['type_rend']

        rdv_datetime = datetime.strptime(f"{date_rdv} {heure_rdv}", "%Y-%m-%d %H:%M")
        now = datetime.now()

        if rdv_datetime < now:
            flash("❌ Impossible de réserver un rendez-vous dans le passé.", "error")
            return redirect(url_for('medecin_ajouter_rendez_vous'))

        # Vérifier si la date du rendez-vous occupé
        cursor.execute("""
            SELECT 1 FROM rendez_vous 
            WHERE date_rend=%s AND heure_rend=%s AND CIN=%s
        """,(date_rdv,heure_rdv,cin))
        if cursor.fetchone():
            flash("❌ déjà réservé.","error")
            return redirect(url_for('medecin_ajouter_rendez_vous'))

        #  créer RDV
        cursor.execute("""
        INSERT INTO rendez_vous(date_rend,heure_rend,type_rend,CIN,NE,statut)
        VALUES (%s,%s,%s,%s,%s,'En_attente')
        """,(date_rdv,heure_rdv,type_rend,cin,id_eleve))
        id_rdv = cursor.lastrowid

        # vérifier dossier ou créer un nouveau
        cursor.execute("SELECT id_dossier FROM dossier WHERE NE=%s",(id_eleve,))
        doss = cursor.fetchone()

        if not doss:
            cursor.execute("INSERT INTO dossier(NE,date_creation) VALUES(%s,CURDATE())",(id_eleve,))
            conn.commit()
            id_dossier = cursor.lastrowid   #  dossier créé
        else:
            id_dossier = doss['id_dossier'] #  dossier existant récupéré

        #  créer consultation liée avec id_dossier inclus
        cursor.execute("""
        INSERT INTO consultation(date_consult,CIN,NE,id_dossier)
        VALUES (%s,%s,%s,%s)
        """,(date_rdv,cin,id_eleve,id_dossier))
        id_consult = cursor.lastrowid

        #  liaison RDV → consultation
        cursor.execute("""
        UPDATE rendez_vous 
        SET id_consultation=%s 
        WHERE id_rend=%s
        """,(id_consult,id_rdv))

        conn.commit()
        flash("Rendez-vous enregistré avec succès 🟢✔","success")
        return redirect(url_for('medecin_consultation', id_consultation=id_consult))

    finally:
        conn.close()



    


#  Liste des élèves
@app.route('/medecin/dossier')
def liste_eleves_dossier():
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT NE, nom_eleve, prénom_eleve, classe_niveau_d_étude FROM Eleve")
    eleves = cur.fetchall()
    db.close()
    return render_template("medecin/liste_eleves.html", eleves=eleves)


@app.route('/medecin/dossier/<int:ne>')
def medecin_dossier(ne):

    db = get_db_connection()
   
    cur = db.cursor()


    # Info élève
    cur.execute("SELECT * FROM Eleve WHERE NE=%s", (ne,))
    eleve = cur.fetchone()

    # Dossier médical
    cur.execute("SELECT * FROM Dossier WHERE NE=%s", (ne,))
    dossier = cur.fetchone()

    
    cur.execute("""
        SELECT c.id_consultation,
               c.date_consult,
               c.état_malade,
               c.analyses,
               o.médicaments,
               o.durée,
               o.date_,
               o.id_ordonnance
        FROM consultation c
        LEFT JOIN ordonnance o ON o.id_consultation = c.id_consultation
        WHERE c.NE = %s
        ORDER BY c.date_consult DESC
    """, (ne,))

    historique = cur.fetchall()

    db.close()
    return render_template("medecin/medecin_dossier.html",
                           eleve=eleve, dossier=dossier, historique=historique)







@app.route('/update_medical/<int:ne>', methods=["POST"])
def update_medical(ne):
    groupe = request.form.get("groupe_sanguin")
    maladie = request.form.get("mld_chr")
    analyses = request.form.get("analyses")
    état_malade = request.form.get("état_malade")
    db = get_db_connection()
    cur = db.cursor()

    # Vérifier si dossier existe
    cur.execute("SELECT id_dossier FROM Dossier WHERE NE=%s", (ne,))
    existe = cur.fetchone()

    if existe:
        # update
        cur.execute("""
            UPDATE Dossier SET groupe_sanguin=%s, mld_chr=%s 
            WHERE NE=%s
        """, (groupe, maladie, ne))
        cur.execute("""
            UPDATE consultation SET analyses=%s, état_malade=%s 
            WHERE NE=%s
        """, (analyses, état_malade, ne))
        flash("Dossier mis à jour avec succès ✔", "success")
    else:
        # insert
        cur.execute("""
            INSERT INTO Dossier (NE, groupe_sanguin, mld_chr, date_creation)
            VALUES (%s, %s, %s, NOW())
        """, (ne, groupe, maladie))
        flash("Dossier créé avec succès ✔", "success")

    db.commit()
    db.close()

    #  redirection correcte
    return redirect(url_for('medecin_dossier', ne=ne))


@app.route('/medecin/historique', methods=['GET', 'POST'])
def medecin_historique():
    if not is_medecin_logged_in():
        return redirect(url_for('medecin_login'))

    conn = get_db_connection()
    if not conn:
        flash('Erreur de connexion à la base de données', 'error')
        return redirect(url_for('medecin_dashboard'))

    ne_search = request.args.get('ne', '').strip()
  # Récupérer la NE entrée dans la barre de recherche

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:

            # Si NE est renseignée → filtrage
            if ne_search:
                cursor.execute("""
                    SELECT r.*, e.nom_eleve, e.prénom_eleve
                    FROM rendez_vous r 
                    JOIN Eleve e ON r.NE=e.NE
                    WHERE r.CIN=%s AND e.NE LIKE %s
                    ORDER BY r.date_rend DESC, r.heure_rend DESC
                """, (session['medecin_id'], f'%{ne_search}%'))

            else:
                cursor.execute("""
                    SELECT r.*, e.nom_eleve, e.prénom_eleve
                    FROM rendez_vous r 
                    JOIN Eleve e ON r.NE=e.NE
                    WHERE r.CIN=%s 
                    ORDER BY r.date_rend DESC, r.heure_rend DESC
                """, (session['medecin_id'],))

            rdv = cursor.fetchall()

        return render_template('medecin/historique.html', rdv=rdv, ne_search=ne_search)

    except Exception as e:
        flash(f"Erreur lors du chargement de l'historique: {str(e)}", 'error')
        return redirect(url_for('medecin_dashboard'))
    finally:
        conn.close()


@app.route('/medecin/modifier', methods=['GET', 'POST'])
def medecin_modifier_info():
    if not is_medecin_logged_in():
        flash('Veuillez vous connecter', 'error')
        return redirect(url_for('medecin_login'))

    connection = get_db_connection()
    if not connection:
        flash('Erreur de connexion à la base de données', 'error')
        return redirect(url_for('medecin_dashboard'))

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            if request.method == 'POST':
                nom = request.form.get('nom')
                prenom = request.form.get('prenom')      
                email = request.form.get('email')
                telephone = request.form.get('telephone')
                ville = request.form.get('ville')  
                adresse = request.form.get('adresse')
                specialite = "Généraliste"                # Fixée ici car on suppose on a un seul medecin au l'école qui est généraliste

                cursor.execute("""
                    UPDATE medecin
                    SET nom_medecin=%s, prénom_medecin=%s, adresse_email=%s,
                        Tele_medecin=%s, adresse_hebergement=%s, ville_hebergement=%s, spécialiste=%s
                    WHERE CIN=%s
                """, (nom, prenom, email, telephone,adresse,ville,specialite, session['medecin_id']))  # session à vérifier

                connection.commit()
                flash("Informations mises à jour avec succès", "success")
                return redirect(url_for('medecin_modifier_info'))

            cursor.execute("SELECT * FROM medecin WHERE CIN=%s", (session['medecin_id'],))
            medecin = cursor.fetchone()
            return render_template('medecin/modifier_info.html', medecin=medecin)

    except Exception as e:
        flash(f"Erreur lors de la modification: {str(e)}", 'error')
        return redirect(url_for('medecin_dashboard'))

    finally:
        connection.close()


#  ROUTE DÉCONNEXION 

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté avec succès', 'info')
    return redirect(url_for('index'))


#  SUPPRESSION DE COMPTE soit par éleve au medecin
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'role' not in session:
        flash("Vous devez être connecté.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        flash("Erreur de connexion à la base de données", "error")
        return redirect(url_for('index'))

    try:
        with conn.cursor() as cur:

            
            # Suppression ELEVE
           
            if session['role'] == 'eleve':
                ne = session.get('eleve_id')   

                if not ne:
                    flash("Identifiant élève introuvable dans la session.", "error")
                    return redirect(url_for('index'))

                cur.execute("DELETE FROM ordonnance WHERE NE=%s", (ne,))
                cur.execute("DELETE FROM consultation WHERE NE=%s", (ne,))
                cur.execute("DELETE FROM rendez_vous WHERE NE=%s", (ne,))
                cur.execute("DELETE FROM dossier WHERE NE=%s", (ne,))
                cur.execute("DELETE FROM users WHERE NE=%s", (ne,))
                cur.execute("DELETE FROM eleve WHERE NE=%s", (ne,))  

            
            # Suppression MEDECIN
           
            elif session['role'] == 'medecin':
                cin = session.get('medecin_id')

                if not cin:
                    flash("Identifiant médecin introuvable.", "error")
                    return redirect(url_for('index'))

                cur.execute("DELETE FROM ordonnance WHERE CIN=%s", (cin,))
                cur.execute("DELETE FROM consultation WHERE CIN=%s", (cin,))
                cur.execute("DELETE FROM rendez_vous WHERE CIN=%s", (cin,))
                cur.execute("DELETE FROM users WHERE CIN=%s", (cin,))
                cur.execute("DELETE FROM medecin WHERE CIN=%s", (cin,))

            conn.commit()
            session.clear()
            flash("Votre compte a été supprimé avec succès.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Erreur lors de la suppression du compte : {e}", "error")
        print("ERREUR suppression :", e)  # utile pour debug

    finally:
        conn.close()

    return redirect(url_for('index'))







if __name__ == '__main__':
    app.run(debug=True)