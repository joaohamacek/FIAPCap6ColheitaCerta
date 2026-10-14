# Colheita Certa — Monitor de perdas na colheita de cana-de-açúcar

**FIAP | Graduação em Inteligência Artificial | Fase 2**  
**Atividade:** Gestão do agronegócio em Python — capítulos 3 a 6  
**Turma:** 1TIAOR

| Integrantes |
|---|
| Leandro de Oliveira |
| João Hamacek |
| Tiago Mendes |

## 1. Problema do agronegócio

O projeto atua no **setor de produção agrícola**, especificamente nas **perdas na colheita da cana-de-açúcar**. O enunciado da FIAP apresenta, como referência contextual, perdas que podem chegar a 15% na colheita mecanizada, comparadas a perdas geralmente inferiores a 5% na manual. O objetivo é converter medições realizadas no campo em informações que ajudem o produtor a identificar operações prioritárias e avaliar o impacto econômico das perdas.

## 2. Solução

O **Colheita Certa** é uma aplicação de linha de comando em Python que:

1. Registra amostragens por talhão, data e frente de colheita (colhedora ou equipe manual).
2. Calcula perda por hectare, percentual, tonelagem estimada, nível de gravidade, prejuízo financeiro e economia potencial ao alcançar a meta.
3. Compara colheita manual e mecanizada e cria rankings por frente e talhão.
4. Recomenda ações conforme a gravidade, configuráveis em `config/parametros.json`.
5. Usa Oracle para armazenamento principal; se estiver offline, registra pendências em JSON para sincronização futura.
6. Permite importar/exportar JSON, gerar TXT e registrar histórico das operações.

**Fluxo:** coleta de amostra → validação → Oracle ou pendências JSON → tabela em memória → indicadores → relatórios.

### Diferenciais

- **Perdas convertidas em R$:** usa preço estimado por tonelada derivado de ATR.
- **Prioridade operacional:** aponta frentes com maior perda percentual.
- **Configuração sem alterar Python:** meta, faixas e recomendações no JSON.
- **Funcionamento offline:** mantém pendências locais para posterior envio ao Oracle.
- **Rastreabilidade:** histórico TXT de inclusões, alterações, exclusões, importações, exportações e sincronizações.

## 3. Regras de cálculo

| Indicador | Fórmula |
|---|---|
| Perda t/ha | (massa recolhida em kg ÷ área amostrada em m²) × 10 |
| Perda percentual | perda t/ha ÷ produtividade t/ha × 100 |
| Cana deixada no campo | perda t/ha × área colhida ha |
| Preço estimado t | ATR em kg/t × preço R$/kg de ATR |
| Prejuízo | toneladas perdidas × preço estimado da tonelada |
| Economia potencial | max(0, perda t/ha − produtividade × meta/100) × área × preço |

A configuração do exemplo usa **127 kg ATR/t** e **R$ 1,0709/kg ATR**, resultando em **R$ 136,0043/t**, exibidos como R$ 136,00/t. São parâmetros de referência reproduzidos do documento-base do projeto; a origem e a vigência desses preços devem ser confirmadas antes de aplicação comercial. O cálculo extrapola uma amostragem para toda a área colhida, portanto representa **uma estimativa didática** e não substitui metodologia amostral agronômica validada.

| Nível | Faixa de perda | Orientação |
|---|---|---|
| BAIXA | Até 5% | Manter/monitorar |
| MEDIA | Acima de 5% até 10% | Ajustar operação |
| ALTA | Acima de 10% até 15% | Avaliar regulagem e treinar |
| CRITICA | Acima de 15% | Suspender para investigar |

## 4. Conteúdos dos capítulos 3 a 6

| Conteúdo exigido | Evidência no projeto |
|---|---|
| Funções com retorno | `perda_t_ha()`, `indicadores()`, `validar()`, `ler_numero()` |
| Procedimentos e parâmetros | `registrar_amostragem(estado)`, `registrar_log(caminho, acao, detalhe)`, `imprimir(linhas)` |
| Lista | Coleção `estado['tabela']`, lote importado e linhas de relatórios |
| Tupla | `TIPOS_COLHEITA`, `MENU`, `COLUNAS` |
| Dicionário | Registros, `estado`, `LIMITES`, `ACOES`, parâmetros e agrupamentos |
| Tabela em memória | Lista de dicionários `estado['tabela']` e visualização em tabela |
| TXT | Gravação de relatórios e histórico, leitura do histórico |
| JSON | Configuração, importação, exportação, pendências e cache |
| Oracle | `src/banco_oracle.py`: conexão, CREATE, INSERT, SELECT, UPDATE, DELETE, commit/rollback e binds |

## 5. Validação dos dados

Os campos são conferidos individualmente. Talhão aceita até 10 caracteres alfanuméricos/hífen; frente aceita até 30; data deve existir e estar entre 2000 e hoje; método é manual/mecânica; números aceitam vírgula ou ponto. Os limites são: área colhida 0,1–5.000 ha, produtividade 20–200 t/ha, área de amostra 1–100 m², massa 0–2.000 kg. A perda calculada não pode superar a produtividade, e perdas maiores que 30% exigem confirmação manual. Itens inválidos em JSON são rejeitados com motivo, e IDs repetidos não são importados.

## 6. Instalação e execução

Pré-requisitos: Python 3.9 ou superior. No terminal, dentro da pasta do projeto:

```bash
pip install -r requirements.txt
python src/main.py
```

No Windows, também pode usar `py src\main.py`.

Na inicialização, digite seu usuário Oracle da FIAP (RM), senha e DSN. O DSN sugerido pelo documento-base é `oracle.fiap.com.br:1521/ORCL`, sujeito à confirmação das informações de conexão disponibilizadas pela instituição. Alternativamente, configure `ORACLE_USER`, `ORACLE_PASSWORD` e `ORACLE_DSN` como variáveis de ambiente. **Nunca publique credenciais no GitHub.** Para executar sem Oracle, pressione ENTER no usuário e o sistema seguirá offline.

Para demonstrar o sistema, escolha **7 (Importar JSON)**, aceite o caminho `dados/exemplo_amostragens.json` e depois escolha **5 (Relatorio)**. O exemplo contém **12 itens válidos e 1 inválido** para demonstrar a validação.

### Menu

| Opção | Ação |
|---|---|
| 1 | Registrar amostragem |
| 2 | Listar amostragens |
| 3 | Atualizar (Oracle obrigatório) |
| 4 | Excluir (Oracle obrigatório) |
| 5 | Relatório e TXT |
| 6 | Exportar JSON |
| 7 | Importar JSON |
| 8 | Sincronizar pendências (Oracle obrigatório) |
| 9 | Histórico de operações |
| 0 | Sair |

## 7. Estrutura

```text
colheita_certa/
├── README.md
├── requirements.txt
├── config/parametros.json
├── dados/exemplo_amostragens.json
├── docs/exemplo_de_execucao.md
├── docs/exemplo_relatorio.txt
├── scripts/criar_tabela_oracle.sql
├── src/main.py
├── src/calculos.py
├── src/validacao.py
├── src/relatorios.py
├── src/arquivos.py
├── src/banco_oracle.py
└── tests/test_calculos.py
```

Os arquivos `saidas/`, `dados/pendentes.json` e `dados/cache_oracle.json` são gerados durante a execução e ignorados pelo Git.

## 8. Testes

```bash
python -m unittest discover -s tests -v
```

Os testes automatizados cobrem fórmulas, classificação e validações. `tests/test_oracle.py` acrescenta testes simulados de conexão, INSERT, SELECT, UPDATE, DELETE, parâmetros SQL (binds), commit/rollback e tratamento de erros. Também verifica a preservação de pendências em JSON quando cadastro, importação ou envio ao Oracle falham e a entrada em modo offline quando a inicialização falha. Os testes usam arquivos temporários e não acessam um servidor Oracle.

**A conexão e a persistência em um Oracle real ainda não foram testadas.** Os mocks verificam o comportamento do código, mas não comprovam compatibilidade SQL, permissões, conectividade ou persistência no servidor. Essa verificação continua necessária para confirmar o requisito de integração Oracle da atividade.

## 9. Referências

- FIAP. Enunciado **Gestão do agronegócio em Python**, capítulos 3 a 6 (fornecido na atividade).
- Documento de referência do grupo: **Colheita Certa — monitor de perdas na colheita de cana-de-açúcar** (README.pdf).
- BOLFE, É. L. et al. *Agricultura digital: pesquisa, desenvolvimento e inovação nas cadeias produtivas*. Embrapa, 2020.
- Oracle. Documentação da biblioteca `python-oracledb`.
