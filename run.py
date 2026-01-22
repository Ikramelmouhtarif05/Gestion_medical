from app import app

if __name__ == '__main__':
    print(" Démarrage de l'application Système Médical...")
    print(" Accès à l'application: http://localhost:5000")
    print(" Pour arrêter l'application: Ctrl+C")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)