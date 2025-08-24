import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from fpdf import FPDF
import base64
from passlib.context import CryptContext
import re

# Estilo CSS para aprimorar a estética dos botões e do layout
st.markdown("""
<style>
    /* Estilo para os botões do menu principal - GRANDE e quadrado */
    [data-testid="stColumn"] .stButton > button {
        width: 200px !important;
        height: 200px !important;
        font-size: 1.8rem !important;
        border-radius: 20px !important;
        border: 2px solid #D3D3D3 !important;
        color: #FFFFFF !important;
        background-color: #4CAF50 !important; /* Cor verde */
        transition: all 0.3s ease;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    [data-testid="stColumn"] .stButton > button:hover {
        background-color: #45a049 !important; /* Um tom de verde mais escuro para o hover */
        border-color: #45a049 !important;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3) !important;
    }
    
    /* Estilos para os botões menores, com !important para forçar a aplicação */
    .stButton > button {
        width: 100% !important;
        height: 40px !important;
        font-size: 1rem !important;
        color: #FFFFFF !important;
        background-color: #4CAF50 !important;
        border-radius: 10px !important;
        border: 1px solid #D3D3D3 !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background-color: #45a049 !important;
    }
    
    /* Ajusta o espaçamento horizontal entre as colunas do menu principal */
    .st-emotion-cache-k7v3i5 {
        gap: 20px;
    }

    h1, h2, h3 {
        color: #333;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .st-bu {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# COLOQUE SUA URL EXTERNA DO BANCO DE DADOS AQUI.
# Ela deve ser copiada diretamente do painel do Render.
DATABASE_URL = "postgresql://escritorio_bd_user:lhoQGcIxFGHZzvgSDGksJAdeTuvpW2Hw@dpg-d2kemap5pdvs739huavg-a.oregon-postgres.render.com/escritorio_bd"

# Caminho para o arquivo do logo
# CERTIFIQUE-SE DE QUE ESTE ARQUIVO ESTÁ NA MESMA PASTA DO app.py
LOGO_PATH = "LOGO lUNA ALENCAR.png"

# Contexto para o hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# --- Funções de Autenticação e Usuários ---

def hash_password(password):
    """Gera um hash para a senha."""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Verifica se a senha em texto simples corresponde ao hash."""
    return pwd_context.verify(plain_password, hashed_password)

def register_user(username, password, role="user"):
    """Salva um novo usuário no banco de dados."""
    conn = create_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            hashed_password = hash_password(password)
            insert_query = "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s);"
            cur.execute(insert_query, (username, hashed_password, role))
            conn.commit()
            st.success(f"Usuário '{username}' cadastrado com sucesso!")
            return True
        except psycopg2.Error as e:
            st.error(f"Erro ao cadastrar usuário: {e}")
            return False
        finally:
            conn.close()
    return False

def get_user(username):
    """Busca um usuário no banco de dados."""
    conn = create_connection()
    user = None
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s;", (username,))
            user = cur.fetchone()
        finally:
            conn.close()
    return user

def update_password(username, new_password):
    """Altera a senha de um usuário."""
    conn = create_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            new_hashed_password = hash_password(new_password)
            update_query = "UPDATE users SET password_hash = %s WHERE username = %s;"
            cur.execute(update_query, (new_hashed_password, username))
            conn.commit()
            st.success("Senha alterada com sucesso!")
            return True
        except psycopg2.Error as e:
            st.error(f"Erro ao alterar senha: {e}")
            return False
        finally:
            conn.close()
    return False

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
        st.error(f"Erro ao inicializar a tabela de usuários: {e}")
        conn.rollback()
    finally:
        cur.close()

def create_initial_tables(conn):
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
            comprovante_anexo TEXT,
            data_pagamento DATE,
            usuario_quitacao VARCHAR(50)
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
    if conn is not None:
        try:
            cur = conn.cursor()
            for command in commands:
                cur.execute(command)
            conn.commit()
            create_users_table_if_not_exists(conn)
        except psycopg2.Error as e:
            st.error(f"Erro ao criar tabelas: {e}")
            conn.rollback()
        finally:
            cur.close()

# --- Funções de formatação ---

def format_cpf_cnpj(cpf_cnpj):
    cpf_cnpj = re.sub(r'\D', '', str(cpf_cnpj))
    if len(cpf_cnpj) == 11:
        return f"{cpf_cnpj[:3]}.{cpf_cnpj[3:6]}.{cpf_cnpj[6:9]}-{cpf_cnpj[9:]}"
    elif len(cpf_cnpj) == 14:
        return f"{cpf_cnpj[:2]}.{cpf_cnpj[2:5]}.{cpf_cnpj[5:8]}/{cpf_cnpj[8:12]}-{cpf_cnpj[12:]}"
    return cpf_cnpj

def format_phone(phone):
    phone = re.sub(r'\D', '', str(phone))
    if len(phone) == 11:
        return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
    elif len(phone) == 10:
        return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
    return phone

# --- Funções de interação com o banco de dados ---

def save_client(nome, cpf_cnpj, telefone, endereco, observacoes):
    """Salva um novo cliente no banco de dados."""
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            insert_query = """
            INSERT INTO clientes (nome_cliente, cpf_cnpj, telefone, endereco, informacoes_adicionais)
            VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(insert_query, (nome, cpf_cnpj, telefone, endereco, observacoes))
            conn.commit()
            st.success("Cliente cadastrado com sucesso!")
        except psycopg2.Error as e:
            st.error(f"Erro ao cadastrar cliente: {e}")
        finally:
            conn.close()

def get_clients(search_query):
    """Busca clientes por nome ou CPF/CNPJ."""
    conn = create_connection()
    clients = []
    if conn:
        try:
            cur = conn.cursor()
            query = """
            SELECT nome_cliente, cpf_cnpj, telefone, endereco
            FROM clientes
            WHERE nome_cliente ILIKE %s OR cpf_cnpj LIKE %s;
            """
            cur.execute(query, (f"%{search_query}%", f"%{search_query}%"))
            clients = cur.fetchall()
        finally:
            conn.close()
    return clients

def get_all_clients():
    """Busca todos os clientes cadastrados no banco de dados."""
    conn = create_connection()
    clients = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id_cliente, nome_cliente FROM clientes ORDER BY nome_cliente;")
            clients = cur.fetchall()
        finally:
            conn.close()
    return clients

def save_contract(id_cliente, descricao, tipo, valor_total, valor_entrada, valor_parcela, data_inicio):
    """Salva um novo contrato no banco de dados."""
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            insert_query = """
            INSERT INTO contratos (id_cliente, descricao_servico, tipo_contrato, valor_total_servico, valor_entrada, valor_parcela, data_inicio)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_contrato;
            """
            cur.execute(insert_query, (id_cliente, descricao, tipo, valor_total, valor_entrada, valor_parcela, data_inicio))
            id_contrato = cur.fetchone()[0]
            conn.commit()
            st.success("Contrato cadastrado com sucesso!")
            return id_contrato
        except psycopg2.Error as e:
            st.error(f"Erro ao cadastrar contrato: {e}")
        finally:
            conn.close()
    return None

def save_installments(id_contrato, num_parcelas, valor_parcela, ultima_parcela, data_inicio):
    """Gera e salva as parcelas de um contrato no banco de dados."""
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            parcela_date = data_inicio
            for i in range(1, num_parcelas + 1):
                parcela_date = parcela_date + timedelta(days=30)
                insert_query = "INSERT INTO parcelas (id_contrato, valor_parcela, data_vencimento, status_pagamento) VALUES (%s, %s, %s, %s);"
                cur.execute(insert_query, (id_contrato, valor_parcela, parcela_date, 'Pendente'))
            
            if ultima_parcela > 0:
                parcela_date = parcela_date + timedelta(days=30)
                cur.execute(insert_query, (id_contrato, ultima_parcela, parcela_date, 'Pendente'))
            
            conn.commit()
            st.success("Parcelas geradas com sucesso!")
        except psycopg2.Error as e:
            st.error(f"Erro ao gerar parcelas: {e}")
        finally:
            conn.close()

def get_client_contracts(client_id):
    """Busca todos os contratos de um cliente específico."""
    conn = create_connection()
    contracts = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id_contrato, descricao_servico FROM contratos WHERE id_cliente = %s;", (client_id,))
            contracts = cur.fetchall()
        finally:
            conn.close()
    return contracts

def get_contract_installments(contract_id):
    """Busca todas as parcelas de um contrato específico."""
    conn = create_connection()
    installments = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id_parcela, valor_parcela, data_vencimento, status_pagamento, forma_pagamento, comprovante_anexo, data_pagamento, usuario_quitacao FROM parcelas WHERE id_contrato = %s ORDER BY data_vencimento ASC;", (contract_id,))
            installments = cur.fetchall()
        finally:
            conn.close()
    return installments

# --- Funções do Sistema ---
def get_user_info_by_parcela(id_parcela):
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            query = """
            SELECT c.nome_cliente, co.descricao_servico FROM parcelas AS p
            JOIN contratos AS co ON p.id_contrato = co.id_contrato
            JOIN clientes AS c ON co.id_cliente = c.id_cliente WHERE p.id_parcela = %s;
            """
            cur.execute(query, (id_parcela,))
            return cur.fetchone()
        finally:
            conn.close()
    return None

def mark_as_paid(id_parcela, forma_pagamento, comprovante_anexo, valor_parcela, username):
    """Atualiza o status de uma parcela para 'Pago' e registra o pagamento."""
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            update_query = """
            UPDATE parcelas SET status_pagamento = 'Pago', data_pagamento = %s, forma_pagamento = %s, comprovante_anexo = %s, usuario_quitacao = %s
            WHERE id_parcela = %s;
            """
            cur.execute(update_query, (date.today(), forma_pagamento, comprovante_anexo, username, id_parcela))
            if forma_pagamento == "Espécie":
                descricao_transacao = f"Pagamento de parcela registrado por {username}."
                add_cash_transaction('entrada', valor_parcela, descricao_transacao)
            conn.commit()
            st.success("Pagamento registrado com sucesso!")
        except psycopg2.Error as e:
            st.error(f"Erro ao registrar pagamento: {e}")
        finally:
            conn.close()

def add_cash_transaction(tipo, valor, descricao):
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            insert_query = "INSERT INTO fluxo_caixa (tipo_movimentacao, valor, descricao) VALUES (%s, %s, %s);"
            cur.execute(insert_query, (tipo, valor, descricao))
            conn.commit()
        finally:
            conn.close()

def get_daily_cash_report(report_date):
    """Gera um relatório do fluxo de caixa diário, com base no saldo do dia anterior."""
    conn = create_connection()
    report = {}
    if conn:
        try:
            cur = conn.cursor()
            yesterday = report_date - timedelta(days=1)
            cur.execute("SELECT tipo_movimentacao, valor FROM fluxo_caixa WHERE DATE(data_movimentacao) < %s;", (report_date,))
            saldo_anterior = sum(t[1] if t[0] == 'entrada' else -t[1] for t in cur.fetchall())
            cur.execute("SELECT tipo_movimentacao, valor, descricao FROM fluxo_caixa WHERE DATE(data_movimentacao) = %s;", (report_date,))
            daily_transactions = cur.fetchall()
            
            total_entradas_hoje = sum(t[1] for t in daily_transactions if t[0] == 'entrada')
            total_saidas_hoje = sum(t[1] for t in daily_transactions if t[0] == 'saida')
            
            saldo_final_hoje = saldo_anterior + total_entradas_hoje - total_saidas_hoje

            report = {
                "saldo_anterior": saldo_anterior,
                "entradas_hoje": total_entradas_hoje,
                "saidas_hoje": total_saidas_hoje,
                "saldo_final": saldo_final_hoje,
                "transacoes_hoje": daily_transactions
            }
        finally:
            conn.close()
    return report

def get_overdue_payments():
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            query = """
            SELECT c.nome_cliente, c.cpf_cnpj, co.descricao_servico, p.valor_parcela, p.data_vencimento FROM parcelas AS p
            JOIN contratos AS co ON p.id_contrato = co.id_contrato
            JOIN clientes AS c ON co.id_cliente = c.id_cliente
            WHERE p.status_pagamento = 'Pendente' AND p.data_vencimento < CURRENT_DATE
            ORDER BY p.data_vencimento ASC;
            """
            cur.execute(query)
            return cur.fetchall()
        finally:
            conn.close()
    return []

# --- Funções de Geração de PDF ---

def create_pdf(title, header, data):
    pdf = FPDF()
    pdf.add_page()
    
    # Adiciona o logo centralizado
    try:
        pdf.image(LOGO_PATH, x=80, y=5, w=50) # Posição y ajustada para o topo
        pdf.ln(30) # Espaço para o logo
    except Exception as e:
        st.error(f"Erro ao carregar a imagem do logo: {e}")
        pdf.ln(10)
    
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt=title, ln=1, align="C")
    
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    
    for col in header:
        pdf.cell(40, 10, txt=col, border=1)
    pdf.ln()

    for row in data:
        for item in row:
            if isinstance(item, date):
                item = item.strftime('%d/%m/%Y')
            elif item is None:
                item = "N/A"
            pdf.cell(40, 10, txt=str(item), border=1)
        pdf.ln()
    
    return bytes(pdf.output(dest='S'))

def generate_cash_report_pdf(report_date):
    report = get_daily_cash_report(report_date)
    pdf = FPDF()
    pdf.add_page()
    
    # Adiciona o logo centralizado
    try:
        pdf.image(LOGO_PATH, x=80, y=5, w=50) # Posição y ajustada para o topo
        pdf.ln(30) # Espaço para o logo
    except Exception as e:
        st.error(f"Erro ao carregar a imagem do logo: {e}")
        pdf.ln(10)
    
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt="Relatório de Caixa do Dia", ln=1, align="C")
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    
    pdf.cell(200, 10, txt=f"Data: {report_date.strftime('%d/%m/%Y')}", ln=1)
    pdf.cell(200, 10, txt=f"Saldo Inicial: R$ {report['saldo_anterior']:.2f}", ln=1)
    pdf.cell(200, 10, txt=f"Total de Entradas: R$ {report['entradas_hoje']:.2f}", ln=1)
    pdf.cell(200, 10, txt=f"Total de Saídas: R$ {report['saidas_hoje']:.2f}", ln=1)
    pdf.cell(200, 10, txt=f"Saldo Final do Dia: R$ {report['saldo_final']:.2f}", ln=1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Transações do Dia", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(40, 10, txt="Tipo", border=1)
    pdf.cell(40, 10, txt="Valor", border=1)
    pdf.cell(100, 10, txt="Descrição", border=1)
    pdf.ln()

    for tipo, valor, descricao in report['transacoes_hoje']:
        pdf.cell(40, 10, txt=tipo.capitalize(), border=1)
        pdf.cell(40, 10, txt=f"R$ {valor:.2f}", border=1)
        pdf.cell(100, 10, txt=descricao, border=1)
        pdf.ln()

    return bytes(pdf.output(dest='S'))

# --- Módulos de Interface ---

def clients_module():
    st.header("Clientes")
    st.info("Aqui você pode cadastrar e consultar clientes.")
    
    if st.button("<- Voltar ao Menu Principal", key="voltar_btn"):
        st.session_state['page'] = 'main'
        st.session_state.pop('client_action', None)
        st.rerun()

    st.markdown("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Cadastrar Novo Cliente", key="cadastrar_cliente_btn"):
            st.session_state['client_action'] = 'cadastrar'
            st.rerun()
    with col_nav2:
        if st.button("Consultar Cliente", key="consultar_cliente_btn"):
            st.session_state['client_action'] = 'consultar'
            st.rerun()

    if 'client_action' not in st.session_state: st.session_state['client_action'] = 'cadastrar'
    
    if st.session_state['client_action'] == 'cadastrar':
        st.subheader("Cadastro de Novo Cliente")
        with st.form("client_form"):
            nome = st.text_input("Nome completo*", placeholder="Nome completo")
            cpf_cnpj = st.text_input("CPF/CNPJ*", placeholder="Apenas números")
            telefone = st.text_input("Telefone", placeholder="Com DDD")
            endereco = st.text_area("Endereço", placeholder="Rua, número, bairro, cidade")
            observacoes = st.text_area("Informações Adicionais", placeholder="Justificativas de atraso, preferências, etc.")
            submitted = st.form_submit_button("Salvar Cliente")
            if submitted:
                if not nome or not cpf_cnpj: st.warning("Por favor, preencha todos os campos obrigatórios (marcados com *).")
                else: save_client(nome, cpf_cnpj, telefone, endereco, observacoes)

    elif st.session_state['client_action'] == 'consultar':
        st.subheader("Consulta de Clientes")
        search_query = st.text_input("Buscar por Nome ou CPF/CNPJ")
        if st.button("Buscar", key="buscar_btn"):
            results = get_clients(search_query)
            if results:
                st.subheader("Resultado da Busca")
                # Formatando os dados antes de exibir no DataFrame
                df_data = []
                for row in results:
                    df_data.append({
                        "Nome": row[0],
                        "CPF/CNPJ": format_cpf_cnpj(row[1]),
                        "Telefone": format_phone(row[2]),
                        "Endereço": row[3]
                    })
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)
            else: st.info("Nenhum cliente encontrado com a busca.")

def contracts_module():
    st.header("Contratos")
    st.info("Aqui você pode cadastrar novos contratos para seus clientes.")

    if st.button("<- Voltar ao Menu Principal", key="voltar_btn"):
        st.session_state['page'] = 'main'
        st.rerun()

    st.markdown("---")

    clients = get_all_clients()
    if not clients: st.warning("Nenhum cliente cadastrado. Por favor, cadastre um cliente primeiro."); return

    client_names = {name: id for id, name in clients}
    selected_name = st.selectbox("Selecione o Cliente*", list(client_names.keys()))
    selected_id = client_names.get(selected_name)

    st.subheader("Detalhes do Contrato")
    descricao = st.text_area("Descrição do Serviço*", placeholder="Descreva o serviço do contrato")
    tipo_contrato = st.radio("Tipo de Contrato", ["Promissória (Valor Fixo)", "Recibo (Valor Variável)"])
    data_inicio = st.date_input("Data de Início do Contrato*", format="DD/MM/YYYY")

    if tipo_contrato == "Promissória (Valor Fixo)":
        with st.form("promissoria_form"):
            valor_total = st.number_input("Valor Total do Serviço*", min_value=0.0, format="%.2f")
            valor_entrada = st.number_input("Valor de Entrada (opcional)", min_value=0.0, format="%.2f")
            valor_parcela = st.number_input("Valor de cada Parcela*", min_value=0.0, format="%.2f")
            submitted = st.form_submit_button("Salvar Contrato")
            if submitted:
                if not descricao or not valor_total or not valor_parcela: st.warning("Por favor, preencha todos os campos obrigatórios (marcados com *).")
                else:
                    saldo = valor_total - valor_entrada
                    num_parcelas = int(saldo / valor_parcela)
                    ultima_parcela = saldo % valor_parcela
                    id_contrato = save_contract(selected_id, descricao, "Promissória", valor_total, valor_entrada, valor_parcela, data_inicio)
                    if id_contrato: save_installments(id_contrato, num_parcelas, valor_parcela, ultima_parcela, data_inicio)

    elif tipo_contrato == "Recibo (Valor Variável)":
        with st.form("recibo_form"):
            st.info("O valor da parcela será calculado automaticamente (30% do valor do benefício).")
            submitted = st.form_submit_button("Salvar Contrato")
            if submitted:
                 if not descricao: st.warning("Por favor, preencha a descrição do serviço.")
                 else:
                    save_contract(selected_id, descricao, "Recibo", None, None, None, data_inicio)
                    st.success("Contrato 'Recibo' criado com sucesso.")

def receipts_module():
    st.header("Recebimentos")
    st.info("Aqui você pode dar baixa em pagamentos de parcelas.")

    if st.button("<- Voltar ao Menu Principal", key="voltar_btn"):
        st.session_state['page'] = 'main'
        st.rerun()

    st.markdown("---")

    clients = get_all_clients()
    if not clients: st.warning("Nenhum cliente cadastrado."); return

    client_names = {name: id for id, name in clients}
    selected_name = st.selectbox("1. Selecione o Cliente", list(client_names.keys()))
    selected_id = client_names.get(selected_name)

    if selected_id:
        contracts = get_client_contracts(selected_id)
        if not contracts: st.info("Este cliente não possui contratos cadastrados."); return
        
        contract_options = {f"{c[1]} (ID: {c[0]})": c[0] for c in contracts}
        selected_contract_key = st.selectbox("2. Selecione o Contrato", list(contract_options.keys()))
        selected_contract_id = contract_options.get(selected_contract_key)

        if selected_contract_id:
            st.subheader("3. Gerenciar Parcelas")
            installments = get_contract_installments(selected_contract_id)
            if not installments: st.info("Nenhuma parcela encontrada para este contrato."); return

            st.write("Parcelas:")
            for i, p in enumerate(installments):
                id_parcela, valor, vencimento, status, forma, comprovante, data_pagamento, usuario_quitacao = p
                
                col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                
                with col1: st.write(f"**Valor:** R$ {valor:.2f}")
                with col2: st.write(f"**Vencimento:** {vencimento.strftime('%d/%m/%Y')}")
                with col3: st.write(f"**Status:** {status}")

                if status == 'Pendente':
                    with col4:
                        if st.button("Marcar como Pago", key=f"pay_button_{id_parcela}"):
                            st.session_state[f'show_pay_form_{id_parcela}'] = True
                else:
                    with col4:
                        st.write(f"**Quitado em:** {data_pagamento.strftime('%d/%m/%Y')}")
                        st.write(f"**Quitado por:** {usuario_quitacao}")

                if st.session_state.get(f'show_pay_form_{id_parcela}', False):
                    with st.form(key=f"pay_form_{id_parcela}"):
                        st.subheader(f"Registrar Pagamento da Parcela #{id_parcela}")
                        forma_pagamento = st.selectbox("Forma de Pagamento", ["Espécie", "Pix", "Depósito"])
                        comprovante_anexo = st.file_uploader("Anexar Comprovante", type=['png', 'jpg', 'jpeg', 'pdf'], key=f"comprovante_{id_parcela}")
                        submitted = st.form_submit_button("Confirmar Pagamento")
                        if submitted:
                            comprovante_nome = comprovante_anexo.name if comprovante_anexo else None
                            mark_as_paid(id_parcela, forma_pagamento, comprovante_nome, valor, st.session_state['username'])
                            st.session_state[f'show_pay_form_{id_parcela}'] = False
                            st.rerun()
                st.markdown("---")

def cash_flow_module():
    st.header("Fluxo de Caixa")
    st.info("Aqui você pode gerenciar entradas e saídas de caixa.")

    if st.button("<- Voltar ao Menu Principal", key="voltar_btn"):
        st.session_state['page'] = 'main'
        st.rerun()

    st.markdown("---")

    st.subheader("Lançar Entrada")
    with st.form("entry_form"):
        valor_entrada = st.number_input("Valor da Entrada*", min_value=0.0, format="%.2f")
        descricao_entrada = st.text_area("Descrição da Entrada*", placeholder="Ex: Pagamento avulso, juros, etc.")
        submitted_entrada = st.form_submit_button("Lançar Entrada")
        if submitted_entrada:
            if not valor_entrada or not descricao_entrada: st.warning("Por favor, preencha todos os campos.")
            else: add_cash_transaction('entrada', valor_entrada, descricao_entrada)

    st.subheader("Lançar Despesa (Saída)")
    with st.form("expense_form"):
        valor_saida = st.number_input("Valor da Despesa*", min_value=0.0, format="%.2f")
        descricao_saida = st.text_area("Descrição da Despesa*", placeholder="Ex: Pagamento de conta de luz, material de escritório...")
        submitted_saida = st.form_submit_button("Lançar Saída")
        if submitted_saida:
            if not valor_saida or not descricao_saida: st.warning("Por favor, preencha todos os campos.")
            else: add_cash_transaction('saida', valor_saida, descricao_saida)

    st.subheader("Transações do Dia")
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            today = date.today()
            cur.execute("SELECT tipo_movimentacao, valor, descricao FROM fluxo_caixa WHERE DATE(data_movimentacao) = %s;", (today,))
            transactions = cur.fetchall()
            if transactions:
                data_to_display = [{"Tipo": t[0].capitalize(), "Valor": f"R$ {t[1]:.2f}", "Descrição": t[2]} for t in transactions]
                st.table(data_to_display)
            else: st.info("Nenhuma transação registrada hoje.")
        finally: conn.close()


def reports_module():
    st.header("Relatórios")
    report_choice = st.radio("Selecione o Relatório", ["Relatório de Caixa", "Relatório de Pagamentos Atrasados"])
    
    if st.button("<- Voltar ao Menu Principal", key="voltar_btn"):
        st.session_state['page'] = 'main'
        st.rerun()

    st.markdown("---")

    if report_choice == "Relatório de Caixa":
        st.subheader("Relatório de Caixa")
        report_date = st.date_input("Selecione a data do relatório", date.today(), format="DD/MM/YYYY")
        
        report = get_daily_cash_report(report_date)
        st.write(f"**Data:** {report_date.strftime('%d/%m/%Y')}")
        st.write(f"**Saldo Anterior:** R$ {report['saldo_anterior']:.2f}")
        st.write(f"**Total de Entradas:** R$ {report['entradas_hoje']:.2f}")
        st.write(f"**Total de Saídas:** R$ {report['saidas_hoje']:.2f}", )
        st.markdown(f"**<font size='+2'>Saldo Final: R$ {report['saldo_final']:.2f}</font>**", unsafe_allow_html=True)
        
        pdf_bytes = generate_cash_report_pdf(report_date)
        st.download_button(
            label="Gerar PDF",
            data=pdf_bytes,
            file_name=f"relatorio_caixa_{report_date.strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf"
        )
    
    elif report_choice == "Relatório de Pagamentos Atrasados":
        st.subheader("Relatório de Pagamentos Atrasados")
        overdue_payments = get_overdue_payments()
        if overdue_payments:
            st.write("Os seguintes pagamentos estão atrasados:")
            st.table(overdue_payments)
            pdf_bytes = create_pdf("Relatório de Pagamentos Atrasados", ["Cliente", "CPF/CNPJ", "Serviço", "Valor", "Vencimento"], overdue_payments)
            st.download_button(label="Gerar PDF", data=pdf_bytes, file_name="pagamentos_atrasados.pdf", mime="application/pdf")
        else: st.info("Parabéns! Nenhum pagamento atrasado encontrado.")
    
def user_management_module():
    st.header("Gerenciamento de Usuários")
    st.info("Aqui você pode cadastrar novos usuários e gerenciar senhas.")
    
    if st.button("<- Voltar ao Menu Principal", key="voltar_btn"):
        st.session_state['page'] = 'main'
        st.rerun()
    
    st.markdown("---")
    
    action = st.radio("Selecione uma ação", ["Cadastrar Usuário", "Alterar Senha"])
    
    if action == "Cadastrar Usuário":
        if st.session_state.get('role') != 'admin':
            st.warning("Você não tem permissão para cadastrar novos usuários.")
            return

        st.subheader("Cadastrar Novo Usuário")
        with st.form("register_form"):
            new_username = st.text_input("Novo Usuário*")
            new_password = st.text_input("Senha*", type="password")
            confirm_password = st.text_input("Confirmar Senha*", type="password")
            role = st.selectbox("Papel", ["user", "admin"])
            submitted = st.form_submit_button("Cadastrar")

            if submitted:
                if not new_username or not new_password or not confirm_password: st.warning("Por favor, preencha todos os campos.")
                elif new_password != confirm_password: st.error("As senhas não coincidem.")
                else: register_user(new_username, new_password, role)
    
    elif action == "Alterar Senha":
        st.subheader("Alterar Sua Senha")
        with st.form("change_password_form"):
            current_password = st.text_input("Senha Atual*", type="password")
            new_password = st.text_input("Nova Senha*", type="password")
            confirm_password = st.text_input("Confirmar Nova Senha*", type="password")
            submitted = st.form_submit_button("Alterar Senha")
            if submitted:
                user = get_user(st.session_state['username'])
                if user and verify_password(current_password, user[2]):
                    if new_password == confirm_password:
                        if update_password(st.session_state['username'], new_password): st.success("Sua senha foi alterada com sucesso!")
                        else: st.error("Ocorreu um erro ao alterar a senha.")
                    else: st.error("As novas senhas não coincidem.")
                else: st.error("Senha atual incorreta.")

# --- Estrutura da Aplicação (Main) ---

def login_page():
    st.title("Acesso ao Sistema de Controle")
    st.markdown("Insira suas credenciais para continuar.")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            user = get_user(username)
            if user and verify_password(password, user[2]):
                st.session_state["logged_in"] = True
                st.session_state["username"] = user[1]
                st.session_state["role"] = user[3]
                st.session_state["page"] = "main"
                st.rerun()
            else: st.error("Usuário ou senha inválidos.")

def main_menu():
    st.sidebar.title(f"Bem-vindo(a), {st.session_state.get('username', 'Usuário')}!")
    if st.sidebar.button("Sair"):
        st.session_state.pop("logged_in", None)
        st.session_state.pop("username", None)
        st.session_state.pop("role", None)
        st.rerun()
    
    st.title("Menu Principal")
    st.markdown("Selecione uma opção abaixo para navegar entre os módulos.")

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clientes", key="clientes_btn"): st.session_state['page'] = 'clientes'; st.rerun()
        if st.button("Contratos", key="contratos_btn"): st.session_state['page'] = 'contratos'; st.rerun()
        if st.button("Recebimentos", key="recebimentos_btn"): st.session_state['page'] = 'recebimentos'; st.rerun()

    with col2:
        if st.button("Fluxo de Caixa", key="fluxo_caixa_btn"): st.session_state['page'] = 'fluxo_caixa'; st.rerun()
        if st.button("Relatórios", key="relatorios_btn"): st.session_state['page'] = 'relatorios'; st.rerun()
        if st.session_state.get('role') == 'admin':
            if st.button("Gerenciar Usuários", key="users_btn"): st.session_state['page'] = 'users'; st.rerun()
        else:
            # Placeholder para manter o alinhamento
            st.markdown('<div class="stButton" style="width: 250px; height: 250px; opacity: 0; pointer-events: none;"></div>', unsafe_allow_html=True)

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state['page'] = 'login'

    if 'tables_initialized' not in st.session_state:
        conn = create_connection()
        if conn:
            create_initial_tables(conn)
            conn.close()
            st.session_state['tables_initialized'] = True
    
    if st.session_state["logged_in"]:
        if st.session_state['page'] == 'main': main_menu()
        elif st.session_state['page'] == 'clientes': clients_module()
        elif st.session_state['page'] == 'contratos': contracts_module()
        elif st.session_state['page'] == 'recebimentos': receipts_module()
        elif st.session_state['page'] == 'fluxo_caixa': cash_flow_module()
        elif st.session_state['page'] == 'relatorios': reports_module()
        elif st.session_state['page'] == 'users': user_management_module()
    else: login_page()


if __name__ == "__main__":
    main()