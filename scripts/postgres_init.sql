-- Initialisation PostgreSQL (même logique que le tutoriel Medium / README).
-- Exécuter en superutilisateur, par exemple :
--   psql -U postgres -f scripts/postgres_init.sql
-- Sous Linux, souvent : sudo -u postgres psql -f scripts/postgres_init.sql
--
-- Personnalisez les noms / mot de passe avant d'exécuter, puis alignez votre .env.

CREATE DATABASE mydatabase;

CREATE USER myuser WITH PASSWORD 'mypassword';

ALTER ROLE myuser SET client_encoding TO 'utf8';
ALTER ROLE myuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE myuser SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE mydatabase TO myuser;

-- PostgreSQL 15+ : le schéma public ne permet plus par défaut à tout le monde
-- de créer des objets. Sans ces droits, Django échoue sur migrate avec
-- « permission denied for schema public ».
\c mydatabase
GRANT ALL ON SCHEMA public TO myuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO myuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO myuser;
