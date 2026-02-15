"""
SISTEMA DATA SHOW - VERSÃO 20.6 (PLATINUM ENTERPRISE FINAL)
===========================================================
Arquitetura: Monolítica Modular (MVC Pattern)
Refatoração: Gemini AI & DevMaycon

ALTERAÇÕES V20.6:
1. [UI] Botões das abas (Painel, Salas, Equipe) aumentados.
2. [UI] Fonte das abas agora é tamanho 15 e Negrito.
3. [SYS] Mantidas todas as correções de placeholder e layout anteriores.
"""

import sys
import os
import sqlite3
import locale
import re
import unicodedata
import hashlib
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# --- Tratamento de Dependências ---
try:
    import customtkinter as ctk
    from PIL import Image as PILImage, ImageTk
except ImportError as e:
    root = tk.Tk(); root.withdraw()
    messagebox.showerror("Erro Crítico", f"Faltam bibliotecas!\nErro: {e}\n\nInstale: pip install customtkinter Pillow reportlab")
    sys.exit()

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, inch
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# =============================================================================
# 1. CONSTANTES GLOBAIS
# =============================================================================
ctk.deactivate_automatic_dpi_awareness()
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# Cores
COR_SUCESSO = "#4CAF50"
COR_PDF = "#2196F3"
COR_ALERTA = "#FF9800"
COR_ERRO = "#F44336"
COR_NEUTRO = "#444444"
COR_DESTAQUE = "#1f6aa5"
COR_BTN_DARK = "#6A1B9A"
COR_BTN_LIGHT = "#FFD700"
COR_ESTRELA_ATIVA = "#FFD700"
COR_ESTRELA_INATIVA = "#555555"
COR_TEXTO_PADRAO = "white"

# Configurações
DB_NOME = 'sistema_datashow_v20_platinum.db'
TITULO_JANELA = "Sistema Data Show v20.6"
TAMANHO_JANELA = "1000x650"
TAMANHO_LOGIN = "400x520"
SALT_SEGURANCA = "SISTEMA_DS_2026_SECURE_KEY_#9988"

EQUIPE_INICIAL = [
    ("RAFAEL", "GERAL"), ("GABRIEL", "GERAL"), ("DAVID", "GERAL"),
    ("FERNANDO", "GERAL"), ("MONTEIRO", "GERAL"), ("MAYCON", "GERAL"),
    ("RYAN", "GERAL"), ("JONATHAN", "AUDITÓRIO"), ("LUCAS", "LÍDER"),
    ("EDUARDO", "LÍDER"),
]
SALAS_INICIAIS = [
    # --- MANHÃ (DIURNO) ---
    ("ADS 2º/3º A", "H - 2º - Sala 02", "MANHÃ"),
    ("CIÊN. COMP 2º/3º A", "H - 2º - Sala 04", "MANHÃ"),
    ("DIREITO 1º A", "F - 1º - Sala 04", "MANHÃ"),
    ("DIREITO 2º/3º A", "F - 1º - Sala 05", "MANHÃ"),
    ("DIREITO 4º/5º A", "F - 1º - Sala 03", "MANHÃ"),
    ("DIREITO 6º/7º A", "F - 1º - Sala 02", "MANHÃ"),
    ("DIREITO 8º/9º A", "F - 1º - Sala 01", "MANHÃ"),
    ("ESTÉTICA E COSM. 2º/3º A", "F - Térreo - Sala 06", "MANHÃ"),
    ("MED. VETERINÁRIA 2º/3º A", "H - 1º - Sala 02", "MANHÃ"),
    ("MED. VETERINÁRIA 4º/5º A", "H - 1º - Sala 03", "MANHÃ"),
    ("MED. VETERINÁRIA 6º/7º A", "H - 1º - Sala 04", "MANHÃ"),
    ("MED. VETERINÁRIA 8º/9º A", "H - 1º - Sala 05", "MANHÃ"),
    ("MED. VETERINÁRIA 10º", "H - 2º - Sala 05", "MANHÃ"),
    ("PSICOLOGIA 2º/3º A", "F - Térreo - Sala 02", "MANHÃ"),
    ("PSICOLOGIA 4º/5º A", "F - Térreo - Sala 03", "MANHÃ"),
    ("PSICOLOGIA 8º/9º A", "F - Térreo - Sala 04", "MANHÃ"),

    # --- NOITE (NOTURNO) ---
    # Tecnólogos
    ("ADS 1º P", "F - 1º - Sala 01", "NOITE"),
    ("ADS 2º P / 3º PQ", "F - 1º - Sala 05", "NOITE"),
    ("ADS 4º PQ", "F - 1º - Sala 02", "NOITE"),
    ("DESIGN GRÁFICO 1º/4º P", "D - 1º - Sala 06", "NOITE"),
    ("DESIGN GRÁFICO 2º/3º P", "D - 1º - Sala 04", "NOITE"),

    # Bacharelados
    ("ADMINISTRAÇÃO 1º P", "B - 2º - Sala 01", "NOITE"),
    ("ADMINISTRAÇÃO 2º/3º P", "B - 2º - Sala 02", "NOITE"),
    ("ADMINISTRAÇÃO 4º/5º P", "B - 2º - Sala 03", "NOITE"),
    ("ADMINISTRAÇÃO 6º/7º P", "B - 2º - Sala 04", "NOITE"),
    ("ARQUITETURA 2º/3º P", "C - Térreo - Sala 2", "NOITE"),
    ("ARQUITETURA 4º/5º P", "C - Térreo - Sala 3", "NOITE"),
    ("ARQUITETURA 6º/7º P", "E - Térreo - Sala 2", "NOITE"),
    ("BIOMEDICINA 2º/3º P", "C - 2º - Sala 03", "NOITE"),
    ("CIÊN. COMP 1º P", "B - 1º - Sala 01", "NOITE"),
    ("CIÊN. COMP 2º P / 3º PQ", "B - 1º - Sala 02", "NOITE"),
    ("CIÊN. COMP 4º P / 5º PQ", "B - 1º - Sala 03", "NOITE"),
    ("CIÊN. COMP 6º P / 7º PQ", "B - 1º - Sala 04", "NOITE"),
    ("CIÊN. CONTÁBEIS 1º P", "B - 2º - Sala 01", "NOITE"),
    ("CIÊN. CONTÁBEIS 2º/3º P", "F - Térreo - Sala 01", "NOITE"),
    ("DIREITO 1º P", "E - 1º - Sala 01", "NOITE"),
    ("DIREITO 2º PQ / 3º PQRS", "E - 1º - Sala 05", "NOITE"),
    ("DIREITO 4º P / 5º P", "E - 1º - Sala 02", "NOITE"),
    ("DIREITO 6º P / 7º PQ", "E - 1º - Sala 06", "NOITE"),
    ("DIREITO 8º PQ / 9º PRS", "E - 2º - Sala 04", "NOITE"),
    ("ENFERMAGEM 2º/3º P", "E - 2º - Sala 05", "NOITE"),
    ("ENFERMAGEM 4º/5º P", "C - 1º - Sala 05", "NOITE"),
    ("ENFERMAGEM 6º/7º P", "C - 1º - Sala 06", "NOITE"),
    ("ENG. BÁSICA 1º PQ", "H - 1º - Sala 3", "NOITE"),
    ("ENG. BÁSICA 1º RS", "H - 1º - Sala 4", "NOITE"),
    ("ENG. BÁSICA 2º P / 3º PQ", "H - 1º - Sala 1", "NOITE"),
    ("ENG. BÁSICA 2º Q / 3º RS", "H - 1º - Sala 2", "NOITE"),
    ("ENG. COMPUTAÇÃO 4º/5º P", "H - 2º - Sala 3", "NOITE"),
    ("ENG. COMPUTAÇÃO 6º/7º P", "H - 1º - Sala 5", "NOITE"),
    ("NUTRIÇÃO 2º/3º P", "C - 2º - Sala 04", "NOITE"),
    ("PSICOLOGIA 2º/3º P", "F - Térreo - Sala 04", "NOITE"),
    ("PSICOLOGIA 4º/5º P", "F - Térreo - Sala 05", "NOITE"),
    ("PSICOLOGIA 6º/7º PQ", "F - Térreo - Sala 06", "NOITE"),
    ("PSICOLOGIA 8º/9º P", "F - Térreo - Sala 07", "NOITE"),
]

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
except:
    try: locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except: pass

# =============================================================================
# 2. UTILITÁRIOS
# =============================================================================
class Utils:
    @staticmethod
    def obter_pasta_base():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def obter_caminho_recurso(nome_arquivo):
        try: base_path = sys._MEIPASS
        except: base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, nome_arquivo)

    @staticmethod
    def garantir_pastas_existem():
        base = Utils.obter_pasta_base()
        for p in ["Relatorios", "Feedbacks"]:
            os.makedirs(os.path.join(base, p), exist_ok=True)

    @staticmethod
    def hash_senha(senha_texto_claro):
        if not senha_texto_claro: return ""
        texto_final = senha_texto_claro + SALT_SEGURANCA
        return hashlib.sha256(texto_final.encode('utf-8')).hexdigest()

    @staticmethod
    def remover_acentos(texto: str) -> str:
        if not texto: return ""
        nfkd = unicodedata.normalize('NFD', texto)
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()

    @staticmethod
    def extrair_info_bloco(texto_bloco: str):
        if not texto_bloco: return "", ""
        texto = texto_bloco.upper()
        letra = ""
        match = re.search(r'([A-Z])\s*-', texto)
        if match: letra = match.group(1)
        andar = ""
        if "SUBSOLO" in texto: andar = "SUBSOLO"
        elif "TERREO" in texto or "TÉRREO" in texto: andar = "TERREO"
        elif "1º" in texto or "1°" in texto or "- 1 -" in texto: andar = "1"
        elif "2º" in texto or "2°" in texto or "- 2 -" in texto: andar = "2"
        return letra, andar

    @staticmethod
    def calcular_penalidade_distancia(bloco_novo, blocos_existentes):
        if not blocos_existentes: return 0
        l_nova, a_novo = Utils.extrair_info_bloco(bloco_novo)
        menor_penalidade = 100
        for b in blocos_existentes:
            l_ex, a_ex = Utils.extrair_info_bloco(b)
            if l_nova == l_ex:
                penalidade = 0 if a_novo == a_ex else 2
            else:
                penalidade = 10
            if penalidade < menor_penalidade: menor_penalidade = penalidade
        return menor_penalidade

# =============================================================================
# 3. BANCO DE DADOS
# =============================================================================
class BancoDeDados:
    def __init__(self):
        self.caminho_db = os.path.join(Utils.obter_pasta_base(), DB_NOME)
        self._inicializar_tabelas()

    def _conectar(self):
        return sqlite3.connect(self.caminho_db, check_same_thread=False, timeout=10)

    def _inicializar_tabelas(self):
        conn = self._conectar()
        c = conn.cursor()
        
        # Tabelas (Mantive igual)
        c.execute("""CREATE TABLE IF NOT EXISTS reservas (
            numero_linha INTEGER, periodo TEXT, professor TEXT, curso TEXT, 
            bloco TEXT, horario_real TEXT, responsavel TEXT, 
            responsavel_auditorio TEXT, contabilizada INTEGER DEFAULT 0,
            PRIMARY KEY (numero_linha, periodo))""")
            
        c.execute("""CREATE TABLE IF NOT EXISTS equipe (
            nome TEXT PRIMARY KEY, carga_acumulada INTEGER DEFAULT 0, 
            disponivel INTEGER DEFAULT 1, especialidade TEXT DEFAULT 'GERAL')""")
            
        c.execute("""CREATE TABLE IF NOT EXISTS salas_turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, curso_semestre TEXT UNIQUE, 
            localizacao TEXT, turno TEXT)""")
            
        c.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
        
        c.execute("""CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nota INTEGER, comentario TEXT, 
            nome_usuario TEXT, email_usuario TEXT, data_envio TEXT)""")
            
        c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha_hash TEXT)""")

        # --- SEED DATA (ATUALIZADO) ---
        
        # Equipe
        c.execute("SELECT count(*) FROM equipe")
        if c.fetchone()[0] == 0:
            for n, e in EQUIPE_INICIAL:
                try: c.execute("INSERT INTO equipe (nome, especialidade) VALUES (?, ?)", (n, e))
                except: pass

        # --- LÓGICA DE ATUALIZAÇÃO AUTOMÁTICA DE SALAS ---
        # Verifica quantas salas tem no banco
        c.execute("SELECT count(*) FROM salas_turmas")
        qtd_banco = c.fetchone()[0]
        qtd_codigo = len(SALAS_INICIAIS)

        # Se o banco estiver vazio OU se a quantidade mudou (você adicionou novas), REFAZ a lista
        if qtd_banco == 0 or qtd_banco != qtd_codigo:
            print("Atualizando lista de salas no banco de dados...") # Log para você ver no terminal
            c.execute("DELETE FROM salas_turmas") # Limpa as antigas
            # Reseta o contador de ID (opcional, mas bom para organização)
            c.execute("DELETE FROM sqlite_sequence WHERE name='salas_turmas'") 
            c.executemany("INSERT INTO salas_turmas (curso_semestre, localizacao, turno) VALUES (?, ?, ?)", SALAS_INICIAIS)

        # Admin Padrão
        c.execute("SELECT count(*) FROM usuarios")
        if c.fetchone()[0] == 0:
            sh = Utils.hash_senha("admin")
            try: c.execute("INSERT INTO usuarios (usuario, senha_hash) VALUES (?, ?)", ("admin", sh))
            except: pass

        conn.commit()
        conn.close()

    # --- Auth ---
    def verificar_login(self, u, s):
        sh = Utils.hash_senha(s)
        with self._conectar() as conn:
            res = conn.execute("SELECT id FROM usuarios WHERE usuario = ? AND senha_hash = ?", (u, sh)).fetchone()
        return bool(res)

    def cadastrar_novo_usuario(self, u, s):
        sh = Utils.hash_senha(s)
        try:
            with self._conectar() as conn:
                conn.execute("INSERT INTO usuarios (usuario, senha_hash) VALUES (?, ?)", (u, sh))
            return True, "Cadastrado com sucesso!"
        except sqlite3.IntegrityError:
            return False, "Usuário já existe."

    # --- Reservas ---
    def listar_todas_reservas(self):
        with self._conectar() as conn:
            return conn.execute("SELECT * FROM reservas ORDER BY numero_linha").fetchall()

    def salvar_reserva(self, dados):
        l = list(dados)
        if len(l) == 8: l.append(0)
        with self._conectar() as conn:
            conn.execute("""INSERT OR REPLACE INTO reservas 
                (numero_linha, periodo, professor, curso, bloco, horario_real, responsavel, responsavel_auditorio, contabilizada) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", l)

    def buscar_conflito_reserva(self, linha, periodo):
        with self._conectar() as conn:
            r = conn.execute("SELECT professor FROM reservas WHERE numero_linha=? AND periodo=?", (linha, periodo)).fetchone()
        return r[0] if r else None

    def listar_linhas_ocupadas_por_periodo(self, periodo):
        with self._conectar() as conn:
            return conn.execute("SELECT numero_linha FROM reservas WHERE periodo=?", (periodo,)).fetchall()

    def limpar_todas_reservas(self):
        with self._conectar() as conn: conn.execute("DELETE FROM reservas")
        
    def incrementar_carga_trabalho(self, nome, linha, periodo):
        with self._conectar() as conn:
            r = conn.execute("SELECT contabilizada FROM reservas WHERE numero_linha=? AND periodo=?", (linha, periodo)).fetchone()
            if r and r[0] == 0:
                conn.execute("UPDATE equipe SET carga_acumulada = carga_acumulada + 1 WHERE nome=?", (nome,))
                conn.execute("UPDATE reservas SET contabilizada = 1 WHERE numero_linha=? AND periodo=?", (linha, periodo))
                return True
        return False

    # --- Equipe ---
    def listar_equipe(self):
        with self._conectar() as conn:
            return conn.execute("SELECT nome, carga_acumulada, disponivel, especialidade FROM equipe ORDER BY nome ASC").fetchall()

    def adicionar_membro(self, nome, esp):
        try:
            with self._conectar() as conn:
                conn.execute("INSERT INTO equipe (nome, especialidade) VALUES (?, ?)", (nome.upper(), esp))
            return True
        except: return False

    def remover_membro(self, nome):
        with self._conectar() as conn: conn.execute("DELETE FROM equipe WHERE nome=?", (nome,))

    def alternar_disponibilidade_membro(self, nome, status_atual):
        novo = 0 if status_atual == 1 else 1 
        if isinstance(status_atual, str):
             novo = 0 if status_atual == "DISPONÍVEL" else 1
        with self._conectar() as conn: conn.execute("UPDATE equipe SET disponivel=? WHERE nome=?", (novo, nome))

    def atualizar_campo_equipe_generico(self, nome_atual, novo_valor, coluna_ui):
        try:
            with self._conectar() as conn:
                if coluna_ui == "Nome":
                    try:
                        conn.execute("UPDATE equipe SET nome=? WHERE nome=?", (novo_valor.upper(), nome_atual))
                        return True
                    except sqlite3.IntegrityError: return False 
                elif coluna_ui == "Especialidade":
                    conn.execute("UPDATE equipe SET especialidade=? WHERE nome=?", (novo_valor, nome_atual))
                    return True
            return False
        except: return False

    # --- Salas ---
    def listar_salas_com_id(self):
        with self._conectar() as conn:
            return conn.execute("SELECT id, curso_semestre, localizacao, turno FROM salas_turmas ORDER BY curso_semestre ASC").fetchall()

    def listar_salas(self): 
        with self._conectar() as conn:
             return conn.execute("SELECT curso_semestre, localizacao, turno FROM salas_turmas ORDER BY curso_semestre ASC").fetchall()

    def salvar_sala(self, c, l, t):
        with self._conectar() as conn:
            conn.execute("INSERT OR REPLACE INTO salas_turmas (curso_semestre, localizacao, turno) VALUES (?, ?, ?)", (c, l, t))

    def remover_sala(self, c):
        with self._conectar() as conn: conn.execute("DELETE FROM salas_turmas WHERE curso_semestre=?", (c,))

    def buscar_local_por_curso(self, c):
        with self._conectar() as conn:
            r = conn.execute("SELECT localizacao FROM salas_turmas WHERE curso_semestre=?", (c,)).fetchone()
        return r[0] if r else None

    def atualizar_campo_sala_por_id(self, id_sala, novo_valor, coluna_ui):
        mapa_colunas = {
            "Curso": "curso_semestre",
            "Turno": "turno",
            "Local": "localizacao"
        }
        campo_db = mapa_colunas.get(coluna_ui)
        if not campo_db: return False
        try:
            with self._conectar() as conn:
                conn.execute(f"UPDATE salas_turmas SET {campo_db}=? WHERE id=?", (novo_valor, id_sala))
            return True
        except: return False

    # --- Configs ---
    def obter_config(self, chave):
        with self._conectar() as conn:
            r = conn.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
        return r[0] if r else None

    def salvar_config(self, chave, valor):
        with self._conectar() as conn:
            conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)", (chave, valor))

    def salvar_feedback(self, n, c, nome, email):
        d = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conectar() as conn:
            conn.execute("INSERT INTO feedbacks (nota, comentario, nome_usuario, email_usuario, data_envio) VALUES (?, ?, ?, ?, ?)", (n, c, nome, email, d))

# =============================================================================
# 4. LÓGICA DE NEGÓCIO
# =============================================================================
class BedelService:
    def __init__(self, db): self.db = db

    def escolher_responsavel_inteligente(self, bloco_alvo):
        equipe = [m for m in self.db.listar_equipe() if m[2] == 1]
        if not equipe: return "SEM EQUIPE"
        
        reservas = self.db.listar_todas_reservas()
        locais = {m[0]: [] for m in equipe}
        carga = {m[0]: m[1] for m in equipe}
        
        for r in reservas:
            resp, bloco = r[6], r[4]
            if resp in locais:
                locais[resp].append(bloco)
                carga[resp] += 1
        
        candidatos = []
        especialistas = []
        eh_auditorio = "AUDITORIO" in Utils.remover_acentos(bloco_alvo)
        
        for nome, _, _, esp in equipe:
            if esp == "AUDITÓRIO": especialistas.append(nome)
            pen = Utils.calcular_penalidade_distancia(bloco_alvo, locais[nome])
            score = (carga[nome] * 3) + pen
            candidatos.append((nome, score))
            
        if eh_auditorio and especialistas:
            return sorted(especialistas, key=lambda n: carga[n])[0]
            
        candidatos.sort(key=lambda x: x[1])
        return candidatos[0][0]

class RelatorioService:
    def __init__(self, db: BancoDeDados):
        self.db = db

    def gerar_pdf(self, data_cabecalho, mes_referencia, ano_referencia):
        try:
            data_limpa = data_cabecalho.replace("/", "-")
            dia_mes = data_limpa[:5]
            nome_arquivo = f"Reserva_{dia_mes}.pdf"
            output_file = os.path.join(os.path.join(Utils.obter_pasta_base(), "Relatorios"), nome_arquivo)
            
            caminho_logo = Utils.obter_caminho_recurso("logo.png")
            doc = SimpleDocTemplate(
                output_file, 
                pagesize=landscape(A4), 
                rightMargin=5*mm, leftMargin=5*mm, topMargin=5*mm, bottomMargin=5*mm
            )
            
            elements = []
            if os.path.exists(caminho_logo):
                im = Image(caminho_logo, width=1.5*inch, height=0.4*inch)
                im.hAlign = 'CENTER'
                elements.append(im)
                elements.append(Spacer(1, 1*mm))
                
            styles = getSampleStyleSheet()
            estilo_titulo = ParagraphStyle('TituloCenter', parent=styles['Normal'], fontSize=12, alignment=1)
            
            reservas = self.db.listar_todas_reservas()
            texto_auditorio = "_______________"
            for r in reservas:
                if len(r) > 7 and r[7] and r[7].strip():
                    texto_auditorio = r[7].strip().upper()
                    break
                    
            titulo = f"<b>RESERVA DE DATA SHOW | DIA: {data_cabecalho} - {mes_referencia.upper()}/{ano_referencia} | AUDITÓRIO: {texto_auditorio}</b>"
            elements.append(Paragraph(titulo, estilo_titulo))
            elements.append(Spacer(1, 3*mm))
            
            linhas_dict = {i: [] for i in range(1, 21)}
            for r in reservas:
                linhas_dict[r[0]].append(r)
                
            lista_ordenada = []
            for num in range(1, 21):
                lista_ordenada.append((num, linhas_dict[num]))
                
            headers = ['Nº', 'HORA', 'PROFESSOR', 'CURSO', 'BLOCO', 'HORÁRIO', 'SOM/MIC', 'RESPONSÁVEL', 'Montou x Desmontou']
            data_tabela = [headers]
            
            tbl_style = [
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TOPPADDING', (0,0), (-1,-1), 1.6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1.6),
                ('LEFTPADDING', (0,0), (-1,-1), 1),
                ('RIGHTPADDING', (0,0), (-1,-1), 1),
                ('LEADING', (0,0), (-1,-1), 9)
            ]
            
            str_som = "SOM( ) MIC( )"
            str_montou = "Montou( ) Desmontou( )"
            row_idx = 1
            
            for num_linha, itens_linha in lista_ordenada:
                def extrair(periodo_key):
                    for item in itens_linha:
                        if item[1] == periodo_key:
                            resp = item[6] if item[6] else ""
                            if resp.strip():
                                self.db.incrementar_carga_trabalho(resp, item[0], item[1])
                            return [item[2], item[3], item[4], item[5], str_som, resp, str_montou]
                    return ["", "", "", "", str_som, "", str_montou]
                    
                tem_manha = any(i[1] in ['M1', 'M2'] for i in itens_linha)
                p1 = 'M1' if tem_manha else '1'
                p2 = 'M2' if tem_manha else '2'
                
                linha1 = [str(num_linha), "1º"] + extrair(p1)
                linha2 = ["", "2º"] + extrair(p2)
                
                data_tabela.append(linha1)
                data_tabela.append(linha2)
                
                tbl_style.append(('SPAN', (0, row_idx), (0, row_idx+1)))
                row_idx += 2
                
            col_widths = [8*mm, 10*mm, 60*mm, 50*mm, 25*mm, 25*mm, 30*mm, 35*mm, 44*mm]
            t = Table(data_tabela, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle(tbl_style))
            elements.append(t)
            
            doc.build(elements)
            
            if os.name == 'nt':
                os.startfile(output_file)
            return True, f"PDF salvo em:\n{output_file}"
        except Exception as e:
            return False, str(e)

# =============================================================================
# 5. UI - LOGIN
# =============================================================================
class LoginWindow(ctk.CTk):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.db = BancoDeDados()
        self.title("Acesso Restrito"); self.geometry(TAMANHO_LOGIN); self.resizable(False, False)
        
        ws = self.winfo_screenwidth(); hs = self.winfo_screenheight()
        x = (ws//2) - (400//2); y = (hs//2) - (580//2)
        self.geometry(f"+{int(x)}+{int(y)}")
        
        card = ctk.CTkFrame(self, corner_radius=20, fg_color="#2b2b2b")
        card.pack(pady=40, padx=40, fill="both", expand=True)
        
        ctk.CTkLabel(card, text="🔐", font=ctk.CTkFont(size=50)).pack(pady=(30, 10))
        ctk.CTkLabel(card, text="SISTEMA DATA SHOW", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(0, 30))
        
        self.u = ctk.CTkEntry(card, placeholder_text="Usuário", height=45, width=280)
        self.u.pack(padx=30, pady=10); self.u.bind("<Return>", lambda e: self.s.focus())
        
        self.s = ctk.CTkEntry(card, placeholder_text="Senha", show="•", height=45, width=280)
        self.s.pack(padx=30, pady=10); self.s.bind("<Return>", self._login)
        
        ctk.CTkButton(card, text="ACESSAR SISTEMA", height=45, width=280, fg_color=COR_SUCESSO, font=ctk.CTkFont(size=14, weight="bold"), command=self._login).pack(padx=30, pady=(30, 15))
        ctk.CTkFrame(card, height=2, fg_color="gray30").pack(fill="x", padx=30, pady=(0, 15))
        ctk.CTkButton(card, text="CADASTRAR NOVO USUÁRIO", height=35, fg_color=COR_NEUTRO, command=self._cadastro).pack(fill="x", padx=30, pady=(0, 20))

    def _login(self, e=None):
        if self.db.verificar_login(self.u.get().strip(), self.s.get().strip()):
            self.quit()
            self.withdraw()
            self.destroy()
            self.on_success()
        else:
            self.s.delete(0, tk.END)
            self.u.focus()
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")

    def _cadastro(self):
        top = ctk.CTkToplevel(self); top.title("Novo Usuário"); top.geometry("350x240")
        top.transient(self); top.grab_set()
        
        x = self.winfo_x() + 175 - 175; y = self.winfo_y() + 290 - 140
        top.geometry(f"+{int(x)}+{int(y)}")
        
        ctk.CTkLabel(top, text="Registro Seguro", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        u = ctk.CTkEntry(top, placeholder_text="Usuário"); u.pack(fill="x", padx=30, pady=10)
        s = ctk.CTkEntry(top, placeholder_text="Senha", show="•"); s.pack(fill="x", padx=30, pady=10)
        
        def save():
            ok, msg = self.db.cadastrar_novo_usuario(u.get().strip(), s.get().strip())
            if ok: messagebox.showinfo("Sucesso", msg); top.destroy()
            else: messagebox.showerror("Erro", msg)
            
        ctk.CTkButton(top, text="CONFIRMAR", fg_color=COR_PDF, command=save).pack(fill="x", padx=30, pady=20)

# =============================================================================
# 6. UI - MAIN APP
# =============================================================================
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        Utils.garantir_pastas_existem()
        self.title(TITULO_JANELA); self.geometry(TAMANHO_JANELA); self.minsize(950, 600)
        
        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(0, weight=1)
        
        self.db = BancoDeDados()
        self.bedel = BedelService(self.db)
        self.pdf = RelatorioService(self.db)
        
        self.linha_selecionada = 1
        self.botoes_grade = {}
        self.id_sala_em_edicao = None
        self.nome_equipe_em_edicao = None
        
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit())
        self.after(500, self._verificar_novo_dia)
        self._construir_interface()
        self.after(200, lambda: self._aplicar_estilo_tabela("Dark"))
        
        self.after(100, lambda: self.focus())

    def _construir_interface(self):
        self.tabs = ctk.CTkTabview(self, width=950)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # --- AUMENTANDO OS BOTÕES DAS ABAS (V20.6) ---
        # Aumentamos a altura e definimos uma fonte maior
        self.tabs._segmented_button.configure(font=ctk.CTkFont(size=15, weight="bold"), height=40)
        
        self.tab_reserva = self.tabs.add("Painel de Reservas")
        self.tab_salas = self.tabs.add("Gestão de Salas")
        self.tab_equipe = self.tabs.add("Gestão de Equipe")
        
        self._setup_rodape()
        self._setup_aba_reservas()
        self._setup_aba_salas()
        self._setup_aba_equipe()

    def _setup_rodape(self):
        rod = ctk.CTkFrame(self, height=40, fg_color="transparent")
        rod.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        rod.grid_columnconfigure(0, weight=1); rod.grid_columnconfigure(1, weight=2); rod.grid_columnconfigure(2, weight=1)
        
        self.btn_tema = ctk.CTkButton(rod, text="MUDAR TEMA", fg_color=COR_BTN_DARK, width=120, command=self._alternar_tema)
        self.btn_tema.grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(rod, text="Sistema Data Show v20.6 | DevMaycon", text_color="gray50").grid(row=0, column=1)
        ctk.CTkButton(rod, text="FEEDBACK", fg_color=COR_NEUTRO, width=100, command=self._feedback).grid(row=0, column=2, sticky="e")

    def _alternar_tema(self):
        m = ctk.get_appearance_mode()
        nm = "Light" if m == "Dark" else "Dark"
        ctk.set_appearance_mode(nm)
        self.btn_tema.configure(fg_color=COR_BTN_LIGHT if nm == "Light" else COR_BTN_DARK, text_color="black" if nm == "Light" else "white")
        self._aplicar_estilo_tabela(nm)

    def _aplicar_estilo_tabela(self, modo):
        s = ttk.Style(); s.theme_use("clam")
        bg = "#F0F0F0" if modo == "Light" else "#2b2b2b"
        fg = "black" if modo == "Light" else "white"
        s.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, borderwidth=0, rowheight=30)
        s.configure("Treeview.Heading", background="#E0E0E0" if modo == "Light" else "#333", foreground=fg, relief="flat")
        s.map("Treeview", background=[('selected', COR_DESTAQUE)])

    def _treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try: l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError: l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for index, (val, k) in enumerate(l): tv.move(k, '', index)
        tv.heading(col, command=lambda: self._treeview_sort_column(tv, col, not reverse))

    # --- ABA RESERVAS ---
    def _setup_aba_reservas(self):
        self.tab_reserva.grid_columnconfigure(0, weight=2)
        self.tab_reserva.grid_columnconfigure(1, weight=1)
        self.tab_reserva.grid_rowconfigure(0, weight=1)

        frame_esq = ctk.CTkFrame(self.tab_reserva, fg_color="transparent")
        frame_esq.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)
        
        card_form = ctk.CTkFrame(frame_esq, border_width=1, border_color="#444", corner_radius=10)
        card_form.pack(fill="both", expand=True)

        ctk.CTkLabel(card_form, text="NOVA RESERVA", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        
        frame_filtros = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_filtros.pack(fill="x", padx=15, pady=5)
        
        self.cb_turno = ctk.CTkComboBox(frame_filtros, values=["Diurno", "Noturno"], width=120, height=30, command=self._att_reserva_ui)
        self.cb_turno.set("Turno")
        self.cb_turno.pack(side="left")
        
        self.var_h = tk.StringVar(value="1")
        ctk.CTkRadioButton(frame_filtros, text="1º Horário", variable=self.var_h, value="1", command=self._att_botoes).pack(side="left", padx=(25, 10))
        ctk.CTkRadioButton(frame_filtros, text="2º Horário", variable=self.var_h, value="2", command=self._att_botoes).pack(side="left")
        
        frame_botoes = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=10, pady=10)
        
        for i in range(10): frame_botoes.grid_columnconfigure(i, weight=1)

        for i in range(1, 21):
            btn = ctk.CTkButton(
                frame_botoes, text=str(i), width=42, height=28, corner_radius=6,
                fg_color=COR_NEUTRO, font=ctk.CTkFont(size=12, weight="bold"), 
                command=lambda x=i: self._sel_linha(x)
            )
            linha = 0 if i <= 10 else 1
            coluna = (i-1) % 10
            btn.grid(row=linha, column=coluna, padx=3, pady=4, sticky="ew")
            self.botoes_grade[i] = btn
            
        self.w_res = {}
        lista_campos = [('prof', 'Nome Professor'), ('curso', 'Curso'), ('bloco', 'Bloco/Sala'), 
                        ('hreal', 'Horário Real'), ('resp', 'Responsável (Auto Atribuir)'), ('audit', 'Responsável Auditório')]
        
        frame_campos = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_campos.pack(fill="both", expand=True, padx=15, pady=5)

        for chave, placeholder in lista_campos:
            if chave in ['curso', 'hreal']:
                widget = ctk.CTkComboBox(frame_campos, values=[], height=32); widget.set(placeholder)
                if chave == 'curso': widget.configure(command=self._auto_local)
            else: 
                widget = ctk.CTkEntry(frame_campos, placeholder_text=placeholder, height=32)
            widget.pack(fill="x", pady=4)
            self.w_res[chave] = widget
            
        ctk.CTkButton(card_form, text="SALVAR RESERVA", height=40, fg_color=COR_SUCESSO, font=ctk.CTkFont(size=14, weight="bold"), command=self._save_reserva).pack(fill="x", padx=15, pady=20)

        frame_dir = ctk.CTkFrame(self.tab_reserva, fg_color="transparent")
        frame_dir.grid(row=0, column=1, sticky="nsew", padx=(2, 5), pady=5)
        
        frame_dir.grid_rowconfigure(0, weight=1)
        frame_dir.grid_rowconfigure(1, weight=0)
        frame_dir.grid_columnconfigure(0, weight=1)
        
        card_pdf = ctk.CTkFrame(frame_dir, border_width=1, border_color="#444", corner_radius=10)
        card_pdf.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        pdf_content = ctk.CTkFrame(card_pdf, fg_color="transparent")
        pdf_content.pack(expand=True, fill="x", padx=20)

        ctk.CTkLabel(pdf_content, text="EXPORTAR RELATÓRIO", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 20))
        
        self.ent_dia = ctk.CTkEntry(pdf_content, height=35, justify="center"); self.ent_dia.insert(0, datetime.now().strftime("%d/%m/%Y")); self.ent_dia.pack(fill="x", pady=6)
        self.ent_mes = ctk.CTkEntry(pdf_content, height=35, justify="center"); self.ent_mes.insert(0, datetime.now().strftime("%B").upper()); self.ent_mes.pack(fill="x", pady=6)
        self.ent_ano = ctk.CTkEntry(pdf_content, height=35, justify="center"); self.ent_ano.insert(0, datetime.now().strftime("%Y")); self.ent_ano.pack(fill="x", pady=6)
        
        self.btn_gerar_pdf = ctk.CTkButton(pdf_content, text="GERAR PDF", height=45, fg_color=COR_PDF, font=ctk.CTkFont(weight="bold"), command=self._gerar_pdf_thread)
        self.btn_gerar_pdf.pack(fill="x", pady=(25, 0))

        card_logo = ctk.CTkFrame(frame_dir, border_width=1, border_color="#444", corner_radius=10)
        card_logo.grid(row=1, column=0, sticky="nsew", pady=(5, 0), ipady=10)
        
        logo_content = ctk.CTkFrame(card_logo, fg_color="transparent")
        logo_content.pack(expand=True, pady=15)
        
        ctk.CTkLabel(logo_content, text="INSTITUIÇÃO", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 5))
        
        self.lbl_logo = ctk.CTkLabel(logo_content, text="[LOGO]", fg_color="transparent")
        self.lbl_logo.pack()
        self._load_logo()
        
        self._att_reserva_ui()
        self._sel_linha(1)

    def _load_logo(self):
        p = Utils.obter_caminho_recurso("logo.png")
        if os.path.exists(p):
            try:
                img = PILImage.open(p)
                tk_img = ctk.CTkImage(img, size=(200, int(img.height*(200/img.width))))
                self.lbl_logo.configure(image=tk_img, text="")
            except: pass

    def _sel_linha(self, n): self.linha_selecionada = n; self._att_botoes()
    
    def _att_reserva_ui(self, e=None):
        t = self.cb_turno.get()
        if t == "Turno": return
        h = ["08:25 - 11:15"] if t == "Diurno" else ["19:10 - 22:00", "19:10 - 20:25", "17:55 - 20:25"]
        self.w_res['hreal'].configure(values=h)
        cursos = [c for c, _, tr in self.db.listar_salas() if (t == "Diurno" and "MANHÃ" in str(tr).upper()) or (t == "Noturno" and "NOITE" in str(tr).upper()) or not tr]
        self.w_res['curso'].configure(values=sorted(list(set(cursos))))
        self._att_botoes()

    def _att_botoes(self):
        t = self.cb_turno.get()
        if t == "Turno": return
        pid = f"M{self.var_h.get()}" if t == "Diurno" else self.var_h.get()
        ocup = [x[0] for x in self.db.listar_linhas_ocupadas_por_periodo(pid)]
        for i, b in self.botoes_grade.items():
            if i == self.linha_selecionada: b.configure(fg_color=COR_DESTAQUE, text=str(i))
            elif i in ocup: b.configure(fg_color=COR_SUCESSO, text="✓")
            else: b.configure(fg_color=COR_NEUTRO, text=str(i))

    def _auto_local(self, c):
        if l := self.db.buscar_local_por_curso(c):
            self.w_res['bloco'].delete(0, tk.END); self.w_res['bloco'].insert(0, l)

    def _save_reserva(self):
        t = self.cb_turno.get()
        if t == "Turno": return messagebox.showwarning("Aviso", "Selecione o Turno.")
        pid = f"M{self.var_h.get()}" if t == "Diurno" else self.var_h.get()
        
        if cf := self.db.buscar_conflito_reserva(self.linha_selecionada, pid):
            if not messagebox.askyesno("Conflito", f"Ocupado por {cf}. Substituir?"): return
            
        d = {k: v.get() for k, v in self.w_res.items()}
        if not d['resp'].strip(): d['resp'] = self.bedel.escolher_responsavel_inteligente(d['bloco'])
        if not all([d['prof'], d['bloco'], d['hreal']]): return messagebox.showwarning("Erro", "Campos obrigatórios vazios.")
        
        c_salvar = "" if d['curso'] == "Curso" else d['curso']
        tupla = (self.linha_selecionada, pid, d['prof'], c_salvar, d['bloco'], d['hreal'], d['resp'], d['audit'])
        self.db.salvar_reserva(tupla)
        
        if self.var_h.get() == "1" and messagebox.askyesno("Replicar", "Copiar para 2º Horário?"):
            p2 = "M2" if t == "Diurno" else "2"
            self.db.salvar_reserva((self.linha_selecionada, p2) + tupla[2:])
            self.var_h.set("2")
            
        self._att_botoes()
        for k, w in self.w_res.items():
            if k in ['curso', 'hreal']: w.set("")
            else: w.delete(0, tk.END)
        if self.linha_selecionada < 20: self._sel_linha(self.linha_selecionada + 1)

    def _gerar_pdf_thread(self):
        def tarefa():
            self.after(0, lambda: self.btn_gerar_pdf.configure(state="disabled", text="Gerando...", fg_color="gray"))
            try:
                ok, msg = self.pdf.gerar_pdf(self.ent_dia.get(), self.ent_mes.get(), self.ent_ano.get())
                if ok: self.after(0, lambda: messagebox.showinfo("Sucesso", msg))
                else: self.after(0, lambda: messagebox.showerror("Erro", msg))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro Crítico", str(e)))
            finally:
                self.after(0, lambda: self.btn_gerar_pdf.configure(state="normal", text="GERAR PDF", fg_color=COR_PDF))
        threading.Thread(target=tarefa, daemon=True).start()

    # --- HELPER DE EDIÇÃO ---
    def _iniciar_edicao_celula(self, event, treeview, callback_salvar):
        region = treeview.identify("region", event.x, event.y)
        if region != "cell": return
        col_id = treeview.identify_column(event.x)
        row_id = treeview.identify_row(event.y)
        if not row_id: return
        col_num = int(col_id.replace("#", "")) - 1
        valores_atuais = treeview.item(row_id, "values")
        valor_atual = valores_atuais[col_num]
        x, y, w, h = treeview.bbox(row_id, col_id)

        def finalizar_edicao(e=None):
            novo_valor = widget.get()
            if callback_salvar(row_id, novo_valor, col_num):
                novos_vals = list(valores_atuais)
                novos_vals[col_num] = novo_valor.upper() if isinstance(widget, tk.Entry) else novo_valor
                treeview.item(row_id, values=novos_vals)
            widget.destroy()

        eh_combo = (treeview == self.tv_s and col_num == 1) or (treeview == self.tv_e and col_num == 3)
        if eh_combo:
            vals = ["MANHÃ", "NOITE"] if treeview == self.tv_s else ["GERAL", "AUDITÓRIO", "LÍDER"]
            widget = ttk.Combobox(treeview, values=vals)
            widget.set(valor_atual)
        else:
            widget = tk.Entry(treeview, bg="#343638", fg="white", insertbackground="white", relief="flat")
            widget.insert(0, valor_atual)
            widget.select_range(0, tk.END)

        widget.place(x=x, y=y, width=w, height=h)
        widget.focus_set()
        widget.bind("<Return>", finalizar_edicao)
        widget.bind("<FocusOut>", lambda e: widget.destroy())

    # --- ABA SALAS (REORGANIZADO V20.5) ---
    def _setup_aba_salas(self):
        top = ctk.CTkFrame(self.tab_salas, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        
        # --- GRUPO CADASTRO (ESQUERDA) ---
        frm_left = ctk.CTkFrame(top, fg_color="transparent")
        frm_left.pack(side="left")

        self.ent_cs = ctk.CTkEntry(frm_left, placeholder_text="Curso (Ex: ADS 1º)", placeholder_text_color="silver", width=180)
        self.ent_cs.pack(side="left", padx=(0, 5))
        
        self.cb_ts = ctk.CTkComboBox(frm_left, values=["MANHÃ", "NOITE"], width=100)
        self.cb_ts.set("Turno")
        self.cb_ts.pack(side="left", padx=5)
        
        self.ent_ls = ctk.CTkEntry(frm_left, placeholder_text="Local (Ex: Sala 01)", placeholder_text_color="silver", width=140)
        self.ent_ls.pack(side="left", padx=5)
        
        self.btn_salvar_sala = ctk.CTkButton(frm_left, text="SALVAR", width=80, fg_color=COR_SUCESSO, command=self._save_sala)
        self.btn_salvar_sala.pack(side="left", padx=5)

        # --- GRUPO PESQUISA (DIREITA) ---
        frm_right = ctk.CTkFrame(top, fg_color="transparent")
        frm_right.pack(side="right")

        self.ent_busca_sala = ctk.CTkEntry(frm_right, placeholder_text="Pesquisar...", placeholder_text_color="silver", width=160)
        self.ent_busca_sala.pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(frm_right, text="PESQUISAR", width=80, command=self._pesquisar_salas).pack(side="left", padx=(0, 0))

        # Treeview
        self.tv_s = ttk.Treeview(self.tab_salas, columns=("Curso", "Turno", "Local"), show="headings")
        
        for c in ("Curso", "Turno", "Local"):
            self.tv_s.heading(c, text=c, command=lambda _c=c: self._treeview_sort_column(self.tv_s, _c, False))
            
        self.tv_s.column("Curso", width=300)
        self.tv_s.column("Turno", width=100, anchor="center")
        self.tv_s.column("Local", width=150)
        self.tv_s.pack(fill="both", expand=True, padx=10)
        
        self.tv_s.bind("<Double-1>", self._ao_editar_sala)
        
        ctk.CTkButton(self.tab_salas, text="REMOVER SELECIONADO", fg_color=COR_ERRO, command=self._del_sala).pack(pady=10)
        self._load_salas()

    def _ao_editar_sala(self, event):
        def salvar_no_db(row_id, valor, col_idx):
            coluna_nome = ["Curso", "Turno", "Local"][col_idx]
            return self.db.atualizar_campo_sala_por_id(row_id, valor, coluna_nome)
        self._iniciar_edicao_celula(event, self.tv_s, salvar_no_db)

    def _load_salas(self):
        for i in self.tv_s.get_children(): self.tv_s.delete(i)
        for id_sala, c, l, t in self.db.listar_salas_com_id():
            self.tv_s.insert("", "end", iid=id_sala, values=(c, t, l))
        
    def _pesquisar_salas(self):
        termo = self.ent_busca_sala.get().strip().upper()
        if not termo:
            self._load_salas()
            return
            
        for i in self.tv_s.get_children(): self.tv_s.delete(i)
        for id_sala, c, l, t in self.db.listar_salas_com_id():
            if termo in c.upper() or termo in l.upper():
                self.tv_s.insert("", "end", iid=id_sala, values=(c, t, l))

    def _save_sala(self):
        c, l, t = self.ent_cs.get(), self.ent_ls.get(), self.cb_ts.get()
        t = "" if t == "Turno" else t
        if not c or not l: return messagebox.showwarning("Aviso", "Preencha Curso e Local.")

        if self.id_sala_em_edicao:
            self.db.atualizar_campo_sala_por_id(self.id_sala_em_edicao, c, "Curso")
            self.db.atualizar_campo_sala_por_id(self.id_sala_em_edicao, l, "Local")
            self.db.atualizar_campo_sala_por_id(self.id_sala_em_edicao, t, "Turno")
            messagebox.showinfo("Sucesso", "Sala atualizada!")
        else:
            self.db.salvar_sala(c, l, t)
        self._load_salas()
        self._reset_form_salas()

    def _del_sala(self):
        if s := self.tv_s.selection(): 
            self.db.remover_sala(self.tv_s.item(s[0])['values'][0])
            self._load_salas()
            self._reset_form_salas()

    def _reset_form_salas(self):
        self.ent_cs.delete(0, tk.END)
        self.ent_ls.delete(0, tk.END)
        self.cb_ts.set("Turno")
        self.id_sala_em_edicao = None
        self.btn_salvar_sala.configure(text="SALVAR", fg_color=COR_SUCESSO)
        self.tab_salas.focus()

    # --- ABA EQUIPE (V20.5) ---
    def _setup_aba_equipe(self):
        top = ctk.CTkFrame(self.tab_equipe, fg_color="transparent"); top.pack(fill="x", padx=10, pady=10)
        
        self.ent_ne = ctk.CTkEntry(top, placeholder_text="Nome do Membro...", placeholder_text_color="silver", width=250)
        self.ent_ne.pack(side="left", padx=5)
        
        self.cb_esp = ctk.CTkComboBox(top, values=["GERAL", "AUDITÓRIO", "LÍDER"], width=180)
        self.cb_esp.set("Especialidade")
        self.cb_esp.pack(side="left", padx=5)
        
        self.btn_add_equipe = ctk.CTkButton(top, text="ADICIONAR", width=100, fg_color=COR_SUCESSO, command=self._add_equipe)
        self.btn_add_equipe.pack(side="left", padx=5)
        
        self.tv_e = ttk.Treeview(self.tab_equipe, columns=("Nome", "Carga", "Status", "Esp"), show="headings")
        
        for c in ("Nome", "Carga", "Status", "Esp"):
            lbl = "Especialidade" if c == "Esp" else c
            self.tv_e.heading(c, text=lbl, command=lambda _c=c: self._treeview_sort_column(self.tv_e, _c, False))
            
        self.tv_e.pack(fill="both", expand=True, padx=10)
        
        self.tv_e.bind("<Double-1>", self._ao_editar_equipe)
        
        bot = ctk.CTkFrame(self.tab_equipe, fg_color="transparent"); bot.pack(pady=10)
        ctk.CTkButton(bot, text="STATUS", fg_color=COR_ALERTA, command=self._toggle_e).pack(side="left", padx=10)
        ctk.CTkButton(bot, text="REMOVER", fg_color=COR_ERRO, command=self._del_equipe).pack(side="left", padx=10)
        self._load_equipe()

    def _ao_editar_equipe(self, event):
        def salvar_no_db(row_id, valor, col_idx):
            valores = self.tv_e.item(row_id, "values")
            nome_antigo = valores[0]
            coluna = ["Nome", "Carga", "Status", "Especialidade"][col_idx]
            if coluna in ["Carga", "Status"]: return False 
            return self.db.atualizar_campo_equipe_generico(nome_antigo, valor, coluna)
        self._iniciar_edicao_celula(event, self.tv_e, salvar_no_db)

    def _load_equipe(self):
        for i in self.tv_e.get_children(): self.tv_e.delete(i)
        for n, c, d, e in self.db.listar_equipe():
            self.tv_e.insert("", "end", values=(n, c, "DISPONÍVEL" if d else "AUSENTE", e))

    def _add_equipe(self):
        e = self.cb_esp.get(); e = "GERAL" if e == "Especialidade" else e
        if self.db.adicionar_membro(self.ent_ne.get(), e): 
            self._load_equipe()
            self._reset_form_equipe()
        else: messagebox.showwarning("Erro", "Nome inválido ou duplicado.")

    def _toggle_e(self):
        if s := self.tv_e.selection():
            i = self.tv_e.item(s[0])['values']
            self.db.alternar_disponibilidade_membro(i[0], i[2])
            self._load_equipe()
            
    def _del_equipe(self):
        if s := self.tv_e.selection(): 
            self.db.remover_membro(self.tv_e.item(s[0])['values'][0])
            self._load_equipe()

    def _reset_form_equipe(self):
        self.ent_ne.delete(0, tk.END)
        self.cb_esp.set("Especialidade")
        self.tab_equipe.focus()

    # --- Utils ---
    def _verificar_novo_dia(self):
        h = datetime.now().strftime("%d/%m/%Y")
        if self.db.obter_config("ult_uso") != h:
            self.db.salvar_config("ult_uso", h)
            if messagebox.askyesno("Novo Dia", f"Data: {h}. Limpar reservas anteriores?"):
                self.db.limpar_todas_reservas(); self._att_botoes()
    
    # --- FEEDBACK ---
    def _feedback(self):
        self.janela_feedback = ctk.CTkToplevel(self)
        self.janela_feedback.title("Enviar Feedback")
        self.janela_feedback.geometry("400x500")
        self.janela_feedback.resizable(False, False)
        self.janela_feedback.transient(self)
        self.janela_feedback.grab_set()
        ctk.CTkLabel(self.janela_feedback, text="Seu feedback é importante!", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(self.janela_feedback, text="Sua avaliação:").pack(pady=(10, 5))
        frm_stars = ctk.CTkFrame(self.janela_feedback, fg_color="transparent")
        frm_stars.pack(pady=5)
        self.botoes_estrelas = []
        self.nota_atual = 5 
        for i in range(1, 6):
            btn = ctk.CTkButton(
                frm_stars, text="★", width=40, height=40, fg_color="transparent", 
                hover_color="#333", font=ctk.CTkFont(size=30), text_color=COR_ESTRELA_ATIVA, 
                command=lambda nota=i: self._atualizar_estrelas(nota)
            )
            btn.pack(side="left", padx=2)
            self.botoes_estrelas.append(btn)
        self.txt_feedback = ctk.CTkTextbox(self.janela_feedback, height=120, width=320, text_color="gray")
        self.txt_feedback.pack(pady=(15, 5))
        self.txt_feedback.insert("1.0", "Comentários, sugestões ou bugs...")
        self.txt_feedback.bind("<FocusIn>", self._foco_entrada_texto)
        self.txt_feedback.bind("<FocusOut>", self._foco_saida_texto)
        self.feedback_placeholder_ativo = True
        ctk.CTkLabel(self.janela_feedback, text="Suas informações (Opcional):", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(15, 5))
        self.ent_fb_nome = ctk.CTkEntry(self.janela_feedback, placeholder_text="Seu Nome", width=320)
        self.ent_fb_nome.pack(pady=5)
        self.ent_fb_email = ctk.CTkEntry(self.janela_feedback, placeholder_text="Seu melhor Email", width=320)
        self.ent_fb_email.pack(pady=5)
        ctk.CTkButton(
            self.janela_feedback, text="ENVIAR FEEDBACK", fg_color=COR_SUCESSO, 
            width=200, command=self._enviar_feedback
        ).pack(pady=30)

    def _atualizar_estrelas(self, nota):
        self.nota_atual = nota
        for i, btn in enumerate(self.botoes_estrelas):
            if i < nota: btn.configure(text_color=COR_ESTRELA_ATIVA)
            else: btn.configure(text_color=COR_ESTRELA_INATIVA)

    def _foco_entrada_texto(self, event):
        if self.feedback_placeholder_ativo:
            self.txt_feedback.delete("1.0", "end")
            self.txt_feedback.configure(text_color=COR_TEXTO_PADRAO)
            self.feedback_placeholder_ativo = False

    def _foco_saida_texto(self, event):
        texto = self.txt_feedback.get("1.0", "end-1c").strip()
        if not texto:
            self.txt_feedback.configure(text_color="gray")
            self.txt_feedback.insert("1.0", "Comentários, sugestões ou bugs...")
            self.feedback_placeholder_ativo = True

    def _enviar_feedback(self):
        texto = "" if self.feedback_placeholder_ativo else self.txt_feedback.get("1.0", "end-1c").strip()
        if not texto:
            messagebox.showwarning("Aviso", "Por favor, escreva algum comentário.")
            return
        try:
            self.db.salvar_feedback(self.nota_atual, texto, self.ent_fb_nome.get().strip(), self.ent_fb_email.get().strip())
            messagebox.showinfo("Sucesso", "Feedback enviado!")
            self.janela_feedback.destroy()
        except Exception as e: messagebox.showerror("Erro", f"Erro: {e}")

if __name__ == "__main__":
    def start():
        app = MainApp()
        app.protocol("WM_DELETE_WINDOW", lambda: (app.withdraw(), app.quit(), sys.exit()))
        app.mainloop()

    login = LoginWindow(start)
    login.protocol("WM_DELETE_WINDOW", lambda: sys.exit())
    login.mainloop()