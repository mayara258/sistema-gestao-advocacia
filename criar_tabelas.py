import psycopg2
from passlib.context import CryptContext

# COLOQUE SUA URL EXTERNA DO BANCO DE DADOS AQUI.
# Ela deve ser copiada diretamente do painel do Render.
DATABASE_URL = "postgresql://escritorio_bd_user:lhoQGcIxFGHZzvgSDGksJAdeTuvpW2Hw@dpg-d2kemap5pdvs739huavg-a.oregon-postgres.render.com/escritorio_bd"

# Contexto para o hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_connection():
    """
    Cria e retorna uma conexão com o banco de dados.
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def hash_password(password):
    """Gera um hash para a senha."""
    return pwd_context.hash(password)

def create_users_table_if_not_exists(conn):
    """Cria a tabela de usuários se ela não existir e insere um usuário admin padrão."""
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(20) NOT NULL
            );
        """)
        
        cur.execute("SELECT COUNT(*) FROM users WHERE username = 'admin';")
        if cur.fetchone()[0] == 0:
            hashed_password = hash_password("admin123")
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s);", ('admin', hashed_password, 'admin'))
        
        conn.commit()
    except psycopg2.Error as e:
        print(f"Erro ao inicializar a tabela de usuários: {e}")
        conn.rollback()
    finally:
        cur.close()


def create_initial_tables():
    """Cria as tabelas do projeto se elas ainda não existirem."""
    commands = (
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente SERIAL PRIMARY KEY,
            nome_cliente VARCHAR(255) NOT NULL,
            cpf_cnpj VARCHAR(20) UNIQUE NOT NULL,
            telefone VARCHAR(20),
            endereco VARCHAR(255),
            informacoes_adicionais TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS contratos (
            id_contrato SERIAL PRIMARY KEY,
            id_cliente INTEGER REFERENCES clientes (id_cliente) ON DELETE CASCADE,
            descricao_servico TEXT NOT NULL,
            tipo_contrato VARCHAR(20) NOT NULL,
            valor_total_servico NUMERIC(10, 2),
            valor_entrada NUMERIC(10, 2),
            valor_parcela NUMERIC(10, 2),
            data_inicio DATE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS parcelas (
            id_parcela SERIAL PRIMARY KEY,
            id_contrato INTEGER REFERENCES contratos (id_contrato) ON DELETE CASCADE,
            valor_parcela NUMERIC(10, 2) NOT NULL,
            data_vencimento DATE NOT NULL,
            status_pagamento VARCHAR(20) NOT NULL,
            forma_pagamento VARCHAR(50),
            comprovante_anexo TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fluxo_caixa (
            id_transacao SERIAL PRIMARY KEY,
            tipo_movimentacao VARCHAR(10) NOT NULL, -- 'entrada' ou 'saida'
            valor NUMERIC(10, 2) NOT NULL,
            descricao TEXT NOT NULL,
            data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn = create_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            for command in commands:
                cur.execute(command)
            conn.commit()
            create_users_table_if_not_exists(conn)
            print("Tabelas criadas com sucesso!")
        except psycopg2.Error as e:
            print(f"Erro ao criar tabelas: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    create_initial_tables()
