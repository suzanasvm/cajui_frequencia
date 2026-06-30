import streamlit as st
import pandas as pd
import holidays
import datetime

# Dicionário para mapear os dias da semana em português para inglês
dias_semana_dict = {
    'Segunda': 'Monday',
    'Terça': 'Tuesday',
    'Quarta': 'Wednesday',
    'Quinta': 'Thursday',
    'Sexta': 'Friday',
    'Sábado': 'Saturday',
    'Domingo': 'Sunday'
}

# Dicionário inverso, para traduzir o nome do dia em inglês de volta para português
dias_semana_dict_inverso = {v: k for k, v in dias_semana_dict.items()}

# Função para definir recessos fixos do calendário 2025 IFNMG - Campus Almenara
def listar_recessos_2025():
    datas = [
        ("2026-01-02", "2026-01-02"),  # Ponto Facultativo
        ("2026-02-16", "2026-02-16"),  # Carnaval - ponto facultativo
        ("2026-02-17", "2026-02-17"),  # Carnaval - ponto facultativo
        ("2026-02-18", "2026-02-18"),  # Quarta-feira de Cinzas - ponto facultativo até as 14h
        ("2026-04-20", "2026-04-20"),  # Ponto Facultativo
        ("2026-05-27", "2026-05-27"),  # Acidente
        ("2026-05-28", "2026-05-28"),  # Acidente
        ("2026-05-29", "2026-05-29"),  # Acidente
        ("2026-06-04", "2026-06-04"),  # Ponto Facultativo - Corpus Christi
        ("2026-06-05", "2026-06-05"),  # Ponto Facultativo
    ]
    frames = [pd.date_range(start=start, end=end, freq='D') for start, end in datas]
    datas_recesso = pd.to_datetime(pd.concat([pd.Series(f) for f in frames])).dt.date
    return pd.DataFrame({'Data de início': datas_recesso})

# Função para definir feriados
def definir_feriados(inicio_semestre):
    feriados_brasil = holidays.Brazil(years=inicio_semestre.year)
    feriados_df = pd.DataFrame({'Data de início': list(feriados_brasil.keys())})
    feriados_df['Data de início'] = pd.to_datetime(feriados_df['Data de início']).dt.date
    return feriados_df

# Função para definir sábados letivos de 2026 conforme calendário IFNMG
def definir_sabados_letivos(dias_da_semana, ano_selecionado):
    dict_sabados = {
        'Monday': [],
        'Tuesday': ['2026-03-14'],
        'Wednesday': [],
        'Thursday': [],
        'Friday': ['2026-04-11']
    }
    datas_sabados = []
    for dia in dias_da_semana:
        datas_sabados.extend([d for d in dict_sabados.get(dia, []) if int(d.split('-')[0]) == ano_selecionado])
    df_sabados_letivos = pd.DataFrame({'Data de início': pd.to_datetime(datas_sabados).date})
    return df_sabados_letivos

# Função auxiliar para reunir TODAS as datas de sábado letivo cadastradas,
# independente dos dias de aula escolhidos pelo usuário.
# Isso é necessário para conseguirmos verificar, para qualquer data,
# se ela é um sábado letivo ou não, mesmo que o usuário não tenha selecionado
# o dia da semana correspondente no multiselect.
def listar_todos_sabados_letivos():
    dict_sabados = {
        'Monday': [],
        'Tuesday': ['2026-03-14'],
        'Wednesday': [],
        'Thursday': [],
        'Friday': ['2026-04-11']
    }
    todas_datas = []
    for lista_datas in dict_sabados.values():
        todas_datas.extend(lista_datas)
    return set(pd.to_datetime(todas_datas).date)

# Interface Streamlit
st.title("Verificador de Aulas Faltantes - Cajui")

ano_selecionado = st.number_input("Ano", min_value=1900, max_value=2100, value=2026, step=1)
uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")

if uploaded_file is not None:
    DIAS_DE_AULA = st.multiselect("Dias de Aula", list(dias_semana_dict.keys()))
    inicio_semestre = st.date_input("Início do Semestre", value=pd.to_datetime('2026-02-04'))
    fim_semestre = st.date_input("Fim do Semestre", value=pd.to_datetime('2026-07-03'))

    aulas_registradas = pd.read_csv(uploaded_file, parse_dates=['Data de início'], dayfirst=True)
    aulas_registradas['Data de início'] = pd.to_datetime(aulas_registradas['Data de início']).dt.date
    aulas_registradas = aulas_registradas.drop_duplicates(subset=['Data de início'])
    aulas_registradas = aulas_registradas[pd.to_datetime(aulas_registradas['Data de início']).dt.year == ano_selecionado]

    dias_da_semana = [dias_semana_dict[d] for d in DIAS_DE_AULA]
    sabados_letivos = definir_sabados_letivos(dias_da_semana, ano_selecionado)

    # Conjunto com TODOS os sábados letivos do calendário, usado só para a checagem final
    todos_sabados_letivos = listar_todos_sabados_letivos()

    datas_semestre = pd.DataFrame({'Data de início': pd.date_range(start=inicio_semestre, end=fim_semestre, freq='D')})
    datas_semestre['Data de início'] = datas_semestre['Data de início'].dt.date

    datas_aulas = datas_semestre[datas_semestre['Data de início'].apply(lambda x: x.strftime('%A')).isin(dias_da_semana)]
    datas_aulas = pd.concat([datas_aulas, sabados_letivos])
    datas_aulas = datas_aulas.sort_values(by='Data de início')
    datas_aulas = datas_aulas[pd.to_datetime(datas_aulas['Data de início']).dt.year == ano_selecionado]

    feriados_periodo = definir_feriados(pd.to_datetime(inicio_semestre))
    recessos_periodo = listar_recessos_2025()

    datas_aulas = datas_aulas[~datas_aulas['Data de início'].isin(feriados_periodo['Data de início'])]
    datas_aulas = datas_aulas[~datas_aulas['Data de início'].isin(recessos_periodo['Data de início'])]

    datas_aulas_faltantes = datas_aulas[~datas_aulas['Data de início'].isin(aulas_registradas['Data de início'])]
    datas_aulas_faltantes = datas_aulas_faltantes.sort_values(by='Data de início')

    # Aqui criamos as duas colunas novas, ANTES de formatar a data como texto.
    # Precisa ser feito antes, porque depois de virar string dd/mm/aaaa
    # não conseguimos mais extrair o dia da semana com strftime.
    datas_aulas_faltantes['Dia da Semana'] = datas_aulas_faltantes['Data de início'].apply(
        lambda x: dias_semana_dict_inverso[x.strftime('%A')] if x.strftime('%A') in dias_semana_dict_inverso else x.strftime('%A')
    )
    datas_aulas_faltantes['Sábado Letivo'] = datas_aulas_faltantes['Data de início'].apply(
        lambda x: 'Sim' if x in todos_sabados_letivos else 'Não'
    )

    st.write("Datas de aulas que NÃO estão registradas:")
    datas_aulas_faltantes['Data de início'] = pd.to_datetime(datas_aulas_faltantes['Data de início']).dt.strftime('%d/%m/%Y')

    # Reordenamos as colunas para que Dia da Semana e Sábado Letivo
    # apareçam logo depois da data, como você pediu.
    datas_aulas_faltantes = datas_aulas_faltantes[['Data de início', 'Dia da Semana', 'Sábado Letivo']]

    st.dataframe(datas_aulas_faltantes)
