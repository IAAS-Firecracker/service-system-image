# Service System Image API

Une API Flask pour gérer les images système dans le cadre du projet Tsore-Iaas-Firecracker.

## Fonctionnalités

- API RESTful complète pour gérer les images système
- Documentation Swagger intégrée
- Connexion à une base de données MySQL
- Gestion des images système pour les machines virtuelles

## Structure de la base de données

Table `system_image` avec les champs suivants :
- `id` : Identifiant unique
- `nom` : Nom de l'image système
- `description` : Description de l'image
- `version` : Version de l'image
- `taille` : Taille de l'image (en GB)
- `chemin` : Chemin d'accès à l'image
- `date_creation` : Date de création de l'image
- `os_type` : Type de système d'exploitation
- `os_version` : Version du système d'exploitation

## Installation

1. Cloner le dépôt :
```
git clone <repository-url>
cd Tsore-Iaas-Firecracker/service-system-image
```

2. Créer un environnement virtuel et l'activer :
```
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installer les dépendances :
```
pip install -r requirements.txt
```

4. Configurer la base de données :
   - Créer une base de données MySQL nommée `service_system_image_db`
   - Modifier le fichier `.env` avec vos informations de connexion

5. Initialiser la base de données :
```
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Utilisation

1. Démarrer le serveur :
```
python3 app.py
```

2. Accéder à l'API :
   - API : http://localhost:5001/api/system-images
   - Documentation Swagger : http://localhost:5001/swagger

## Endpoints API

- `GET /api/system-images` : Liste toutes les images système
- `POST /api/system-images` : Crée une nouvelle image système
- `GET /api/system-images/<id>` : Obtient une image système par son ID
- `PUT /api/system-images/<id>` : Met à jour une image système
- `DELETE /api/system-images/<id>` : Supprime une image système
- `GET /api/system-images/search/<nom>` : Recherche des images système par nom
- `GET /api/system-images/os/<os_type>` : Obtient les images système par type de système d'exploitation

## Configuration .env docker

```
SECRET_KEY=your_secret_key_here
MYSQL_HOST=mysql_db_service_system_image
MYSQL_PORT=3306
MYSQL_USER=firecracker
MYSQL_PASSWORD=firecracker
MYSQL_DB=service_system_image_db
APP_PORT=5001
SERVICE_CONFIG_URI=http://service-config:8080
APP_NAME=service-system-image
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
EUREKA_SERVER=http://service-registry:8761/eureka/
```

## Configuration .env local

```
# Service System Image
SECRET_KEY=4b4017b60ba6766fa68ac34cda732625aceb1248483b363507c62a76aeb0fb3d5df4fbec77ebb94c409294ff1597ac093cee490e1e842674ab3c989a2162b1104214f0c802fe1d3ca8cbc823b162fc6fd986c53147a0a5b23467238feb9ff9c0f92135dbee5710550466a1013b20abd96496f61c1b44d74e9b3438c8fefa89cd

APP_PORT=5001
MYSQL_HOST=localhost
MYSQL_PORT=13319
MYSQL_DB=service_system_image_db
MYSQL_USER=firecracker
MYSQL_PASSWORD=firecracker
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
EUREKA_SERVER=http://localhost:8761/eureka/

SERVICE_CONFIG_URI=http://localhost:8080
APP_NAME=service-system-image
```
