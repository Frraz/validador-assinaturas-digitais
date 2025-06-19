# Validador de Assinaturas Digitais em Massa

Um sistema para validação de assinaturas digitais em documentos PDF, com suporte especial para certificados ICP-Brasil.

## Características

- Validação criptográfica de múltiplos documentos PDF em uma única operação
- Suporte para certificados ICP-Brasil
- Geração de relatórios detalhados
- Interface web amigável
- Processamento assíncrono
- Verificação criptográfica das assinaturas

## Requisitos do Sistema

- Python 3.8 ou superior
- PostgreSQL (opcional, também suporta SQLite)
- Dependências Python listadas em `requirements.txt`

## Instalação com Docker
```bash
# Clone o repositório
git clone https://github.com/Frraz/validador-assinaturas-digitais.git
cd validador-assinaturas-digitais

# Construa e execute o container Docker
docker build -t validador-assinaturas .
docker run -p 8000:8000 validador-assinaturas
```

## Instalação para Produção
Para ambientes de produção, recomendamos:

**Usar PostgreSQL como banco de dados:**

```bash
export DATABASE_URL=postgresql://usuario:senha@localhost/validador_assinaturas
```

**Configurar um servidor web como Nginx:**

```nginx
server {
    listen 80;
    server_name seudominio.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Usar um gerenciador de processos como o Supervisor:**

```ini
[program:validador]
command=/caminho/para/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/caminho/para/validador-assinaturas-digitais
autostart=true
autorestart=true
stderr_logfile=/var/log/validador.err.log
stdout_logfile=/var/log/validador.out.log
user=www-data
```

## 📝 Configuração
O sistema pode ser configurado através de variáveis de ambiente:

| Variável              | Descrição                             | Valor Padrão                     |
|-----------------------|---------------------------------------|----------------------------------|
| `DATABASE_URL`        | URI de conexão com o banco de dados   | `sqlite:///./signatures.db`      |
| `MAX_FILE_SIZE`       | Tamanho máximo de arquivo em bytes    | `10485760` (10MB)                |
| `FILE_RETENTION_DAYS` | Período de retenção para uploads      | `7`                              |
| `REPORT_RETENTION_DAYS`| Período de retenção para relatórios   | `30`                             |
| `LOG_LEVEL`           | Nível de detalhamento dos logs        | `INFO`                           |

## 💻 Como Usar

### Interface Web
1. Acesse a aplicação em seu navegador: `http://localhost:8000`
2. Arraste e solte os documentos PDF ou clique em "Selecionar Arquivos"
3. Clique em "Iniciar Validação" para processar os documentos
4. Acompanhe o progresso da validação em tempo real
5. Ao finalizar, baixe o relatório completo em PDF

### API REST
O sistema também oferece uma API REST completa:

| Endpoint         | Método | Descrição                               |
|------------------|--------|-------------------------------------------|
| `/upload/`       | POST   | Upload de arquivos para validação         |
| `/status/{job_id}`| GET    | Verifica o status de um processo de validação |
| `/report/{job_id}`| GET    | Baixa o relatório de validação            |

**Exemplo de uso com cURL:**

```bash
# Upload de arquivos
curl -X POST -F "files=@documento1.pdf" -F "files=@documento2.pdf" http://localhost:8000/upload/

# Verificar status
curl http://localhost:8000/status/123e4567-e89b-12d3-a456-426614174000

# Baixar relatório
curl -O http://localhost:8000/report/123e4567-e89b-12d3-a456-426614174000
```

## 🧠 Funcionamento Técnico

### Validação de Assinaturas
O sistema implementa um processo abrangente de validação:

1.  **Verificação de Integridade:** Garante que o documento não foi modificado após a assinatura
2.  **Validação do Certificado:** Verifica se o certificado do assinante é válido e não está expirado
3.  **Verificação da Cadeia:** Valida toda a cadeia de certificação até a autoridade raiz
4.  **Verificação de Revogação:** Consulta LCRs e serviços OCSP (quando disponível)
5.  **Análise da ICP-Brasil:** Verificações específicas para certificados da ICP-Brasil

### Processos Internos
**Diagrama de Processo**

1.  **Upload e Validação Inicial:** Verificação de formato, tamanho e conteúdo
2.  **Processamento Assíncrono:** Análise criptográfica das assinaturas
3.  **Extração de Informações:** Dados do assinante, momento da assinatura, razão
4.  **Validação Criptográfica:** Verificação da integridade e autenticidade
5.  **Geração de Relatório:** Compilação dos resultados em PDF detalhado

## 🏗️ Estrutura do Projeto
```
validador-assinaturas-digitais/
├── app/
│   ├── main.py                    # Endpoints da API FastAPI
│   ├── static/                    # Recursos estáticos (CSS, JS)
│   │   ├── css/styles.css         # Estilos CSS
│   │   └── js/main.js             # Scripts JavaScript
│   ├── validation/                # Lógica de validação
│   │   ├── signature_validator.py # Validação de assinaturas
│   │   └── icp_brasil.py          # Validação específica ICP-Brasil
│   ├── report/                    # Geração de relatórios
│   │   └── pdf_generator.py       # Geração de relatórios PDF
│   └── database/                  # Camada de persistência
│       ├── models.py              # Modelos SQLAlchemy
│       └── database.py            # Configuração do banco de dados
├── templates/                     # Templates HTML
│   └── index.html                 # Página principal da aplicação
├── uploads/                       # Diretório para arquivos enviados
├── reports/                       # Diretório para relatórios gerados
├── tests/                         # Testes unitários e de integração
│   ├── test_signature_validator.py # Testes de validação
│   ├── test_icp_brasil.py         # Testes para ICP-Brasil
│   └── test_integration.py        # Testes de integração
├── docs/                          # Documentação adicional
│   └── images/                    # Imagens para documentação
├── docker/                        # Arquivos para containerização
├── Dockerfile                     # Configuração Docker
├── docker-compose.yml             # Configuração Docker Compose  
├── requirements.txt               # Dependências do projeto
├── README.md                      # Este arquivo
└── LICENSE                        # Licença do projeto
```

## 🧪 Testando a Aplicação
Execute os testes unitários e de integração:

```bash
# Executar todos os testes
python -m pytest

# Executar testes específicos
python -m pytest tests/test_signature_validator.py

# Executar com relatório de cobertura
python -m pytest --cov=app tests/
```

### Conjuntos de Teste
Para fins de desenvolvimento e teste, o repositório inclui documentos PDF de exemplo:

-   `tests/resources/valid_signed.pdf`: Documento com assinatura válida
-   `tests/resources/invalid_signed.pdf`: Documento com assinatura inválida
-   `tests/resources/icp_brasil_signed.pdf`: Documento com assinatura ICP-Brasil

## 🛡️ Segurança
O sistema implementa as seguintes medidas de segurança:

-   **Validação Rigorosa:** Verifica tipo, tamanho e conteúdo dos arquivos
-   **Processamento Isolado:** Cada arquivo é processado em contexto isolado
-   **Limpeza Automática:** Remoção programada de arquivos temporários
-   **Limites de Tamanho:** Controle no tamanho dos arquivos aceitos
-   **Sanitização de Entrada:** Proteção contra injeção e ataques

## 🔧 Solução de Problemas

### Problemas Comuns
**P: A aplicação não inicia corretamente**
R: Verifique se todas as dependências estão instaladas e se as permissões dos diretórios estão corretas.

**P: Erro ao validar um documento específico**
R: Verifique se o PDF está correto e não está corrompido. Alguns formatos de assinatura muito específicos podem não ser suportados.

**P: Tempo de processamento muito longo**
R: O tempo de processamento depende do tamanho dos documentos, da quantidade de assinaturas e da necessidade de consultas online (OCSP/LCR).

### Logs do Sistema
Para resolver problemas mais complexos, verifique os logs:

```bash
# Logs do uvicorn
tail -f uvicorn.log

# Logs da aplicação (quando configurado)
tail -f /var/log/validador.log
```

## 🔄 Atualizações e Manutenção

### Atualizando a Aplicação
```bash
# Atualizar o código
git pull origin main

# Atualizar dependências
pip install -r requirements.txt --upgrade

# Verificar/aplicar migrações do banco de dados
alembic upgrade head
```

### Backup e Restauração
```bash
# Backup do banco de dados (PostgreSQL)
pg_dump -U usuario -d validador_assinaturas > backup.sql

# Restaurar banco de dados
psql -U usuario -d validador_assinaturas < backup.sql

# Backup de arquivos importantes
tar -czf validador_backup.tar.gz reports/ uploads/
```

## 🤝 Contribuindo
Contribuições são bem-vindas! Para contribuir:

1.  Faça um fork do repositório
2.  Crie uma branch para sua feature: `git checkout -b feature/nova-funcionalidade`
3.  Faça commit das suas alterações: `git commit -m 'Adiciona nova funcionalidade'`
4.  Envie para o seu fork: `git push origin feature/nova-funcionalidade`
5.  Abra um Pull Request para a branch `main`

### Diretrizes para Contribuição
- Escreva testes para novas funcionalidades
- Siga o estilo de código existente
- Documente código e funcionalidades
- Verifique se todos os testes passam antes de submeter

## 📚 Recursos Adicionais
- [Especificações da ICP-Brasil](http://www.iti.gov.br/icp-brasil/documentos)
- [Documentação do PyHanko](https://pyhanko.readthedocs.io/en/stable/)
- [Documentação do FastAPI](https://fastapi.tiangolo.com/)

## 📄 Licença
Este projeto está licenciado sob a Licença MIT - veja o arquivo `LICENSE` para detalhes.

## 👨‍💻 Autor
**Warley Ferraz**

-   GitHub: [Frraz](https://github.com/Frraz)

---
*Última atualização: 19 de junho de 2025*
*Versão atual: 1.2.0*