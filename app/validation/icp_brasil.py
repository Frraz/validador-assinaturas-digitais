import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from cryptography import x509

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('icp_brasil_validator')

# OIDs específicos da ICP-Brasil
ICP_BRASIL_OID_BASE = "2.16.76.1.2"
ICP_BRASIL_PERSON_OID = "2.16.76.1.3.1"
ICP_BRASIL_CNPJ_OID = "2.16.76.1.3.3"
ICP_BRASIL_AC_RAIZ = "2.16.76.1.1"

# Lista de ACs conhecidas na hierarquia da ICP-Brasil
ICP_BRASIL_AC_NAMES = [
    "AC RAIZ",
    "AC SERPRO",
    "AC CAIXA",
    "AC SERASA",
    "AC CERTISIGN",
    "AC SOLUTI",
    "AC VALID",
    "AC DOCCLOUD",
    "AC DIGITALSIGN",
    "AC PRODEMGE"
]


def check_if_icp_brasil(cert) -> bool:
    """
    Verifica se um certificado pertence à ICP-Brasil
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        bool: True se for certificado da ICP-Brasil, False caso contrário
    """
    try:
        # 1. Verificar OIDs específicos da ICP-Brasil
        for extension in cert.extensions:
            oid_str = str(extension.oid.dotted_string)
            if oid_str.startswith(ICP_BRASIL_OID_BASE) or oid_str.startswith(ICP_BRASIL_PERSON_OID) or oid_str == ICP_BRASIL_AC_RAIZ:
                return True
                
        # 2. Verificar no emissor se contém informações da ICP-Brasil
        issuer_str = str(cert.issuer)
        if any(ac_name.upper() in issuer_str.upper() for ac_name in ICP_BRASIL_AC_NAMES) or "ICP-BRASIL" in issuer_str.upper():
            return True
        
        # 3. Verificar subject para certificados de AC
        subject_str = str(cert.subject)
        if "ICP-BRASIL" in subject_str.upper() or any(ac_name.upper() in subject_str.upper() for ac_name in ICP_BRASIL_AC_NAMES):
            return True
            
        # 4. Verificar políticas de certificados
        for extension in cert.extensions:
            if extension.oid.dotted_string == "2.5.29.32":  # Certificate Policies
                policies = extension.value
                for policy in policies:
                    policy_oid = policy.policy_identifier.dotted_string
                    if policy_oid.startswith(ICP_BRASIL_OID_BASE):
                        return True
            
        return False
        
    except Exception:
        logger.exception("Erro ao verificar se certificado é ICP-Brasil")
        return False


def extract_icp_brasil_info(cert) -> Dict[str, Any]:
    """
    Extrai informações específicas de certificados ICP-Brasil
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        Dicionário com informações do certificado ICP-Brasil
    """
    info = {
        "is_icp_brasil": False,
        "certificate_type": "Desconhecido",
        "person_info": {},
        "organization_info": {},
        "issuer": str(cert.issuer),
        "valid_from": cert.not_valid_before.strftime("%d/%m/%Y %H:%M:%S"),
        "valid_until": cert.not_valid_after.strftime("%d/%m/%Y %H:%M:%S"),
        "serial_number": str(cert.serial_number)
    }
    
    try:
        # Verificar se é ICP-Brasil
        is_icp_brasil = check_if_icp_brasil(cert)
        if not is_icp_brasil:
            return info
            
        info["is_icp_brasil"] = True
        
        # Detectar tipo de certificado (A1, A3, etc.)
        cert_type = detect_certificate_type(cert)
        info["certificate_type"] = cert_type
        
        # Extrair dados da pessoa física (CPF)
        cpf = extract_cpf_from_certificate(cert)
        if cpf:
            info["person_info"]["cpf"] = cpf
        
        # Extrair nome do titular
        subject_common_name = extract_common_name(cert)
        if subject_common_name:
            info["person_info"]["name"] = subject_common_name
        
        # Extrair dados de pessoa jurídica (CNPJ)
        cnpj = extract_cnpj_from_certificate(cert)
        if cnpj:
            info["organization_info"]["cnpj"] = cnpj
        
        # Extrair nome da organização
        org_name = extract_organization_name(cert)
        if org_name:
            info["organization_info"]["name"] = org_name
        
        # Extrair nível do certificado (A1, A3)
        policy_level = extract_policy_level(cert)
        if policy_level:
            info["policy_level"] = policy_level
        
        return info
        
    except Exception as e:
        logger.exception(f"Erro ao extrair informações ICP-Brasil: {e}")
        return info


def detect_certificate_type(cert) -> str:
    """
    Detecta o tipo de certificado ICP-Brasil
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        String indicando o tipo de certificado
    """
    try:
        # Verificar policies para determinar o tipo
        for extension in cert.extensions:
            if extension.oid.dotted_string == "2.5.29.32":  # Certificate Policies
                policies = extension.value
                for policy in policies:
                    policy_oid = policy.policy_identifier.dotted_string
                    
                    # A1 - Certificado de assinatura tipo A1
                    if policy_oid == "2.16.76.1.2.1.1":
                        return "A1 - Pessoa Física"
                    elif policy_oid == "2.16.76.1.2.1.2":
                        return "A1 - Pessoa Jurídica"
                    
                    # A3 - Certificado de assinatura tipo A3
                    elif policy_oid == "2.16.76.1.2.3.1":
                        return "A3 - Pessoa Física"
                    elif policy_oid == "2.16.76.1.2.3.2":
                        return "A3 - Pessoa Jurídica"
                    
                    # A4 - Certificado de assinatura tipo A4
                    elif policy_oid == "2.16.76.1.2.4.1":
                        return "A4 - Pessoa Física"
                    elif policy_oid == "2.16.76.1.2.4.2":
                        return "A4 - Pessoa Jurídica"
        
        # Verificar se tem informações de pessoa física ou jurídica
        if extract_cpf_from_certificate(cert):
            if extract_cnpj_from_certificate(cert):
                return "Certificado ICP-Brasil (PF e PJ)"
            else:
                return "Certificado ICP-Brasil (PF)"
        elif extract_cnpj_from_certificate(cert):
            return "Certificado ICP-Brasil (PJ)"
        
        return "Certificado ICP-Brasil"
        
    except Exception:
        logger.exception("Erro ao detectar tipo de certificado")
        return "Certificado Digital"


def extract_cpf_from_certificate(cert) -> Optional[str]:
    """
    Extrai o CPF do certificado ICP-Brasil
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        String com o CPF formatado ou None se não encontrado
    """
    try:
        # Buscar OID específico do CPF na ICP-Brasil
        for extension in cert.extensions:
            if extension.oid.dotted_string == ICP_BRASIL_PERSON_OID:
                # O valor deve conter o CPF
                extension_data = extension.value.value
                if len(extension_data) >= 11:
                    cpf = ''.join(chr(c) for c in extension_data[:11])
                    # Formatar CPF
                    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        
        # Alternativa: procurar no Subject Alternative Name
        for extension in cert.extensions:
            if extension.oid.dotted_string == "2.5.29.17":  # subjectAltName
                for name in extension.value:
                    if name.type_id == "2.5.29.17.1":  # otherName
                        if ICP_BRASIL_PERSON_OID in str(name.value):
                            return re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', str(name.value)).group(1)
        
        # Alternativa: verificar o subject RDN
        subject_str = str(cert.subject)
        cpf_match = re.search(r'CPF[:=\s]+(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})', subject_str)
        if cpf_match:
            cpf = cpf_match.group(1)
            if len(cpf) == 11:  # CPF sem formatação
                return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
            return cpf
            
        return None
        
    except Exception:
        logger.exception("Erro ao extrair CPF do certificado")
        return None


def extract_cnpj_from_certificate(cert) -> Optional[str]:
    """
    Extrai o CNPJ do certificado ICP-Brasil
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        String com o CNPJ formatado ou None se não encontrado
    """
    try:
        # Buscar OID específico do CNPJ na ICP-Brasil
        for extension in cert.extensions:
            if extension.oid.dotted_string == ICP_BRASIL_CNPJ_OID:
                # O valor deve conter o CNPJ
                extension_data = extension.value.value
                if len(extension_data) >= 14:
                    cnpj = ''.join(chr(c) for c in extension_data[:14])
                    # Formatar CNPJ
                    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        
        # Alternativa: procurar no Subject Alternative Name
        for extension in cert.extensions:
            if extension.oid.dotted_string == "2.5.29.17":  # subjectAltName
                for name in extension.value:
                    if name.type_id == "2.5.29.17.1":  # otherName
                        if ICP_BRASIL_CNPJ_OID in str(name.value):
                            return re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', str(name.value)).group(1)
        
        # Alternativa: verificar o subject RDN
        subject_str = str(cert.subject)
        cnpj_match = re.search(r'CNPJ[:=\s]+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})', subject_str)
        if cnpj_match:
            cnpj = cnpj_match.group(1)
            if len(cnpj) == 14:  # CNPJ sem formatação
                return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            return cnpj
            
        return None
        
    except Exception:
        logger.exception("Erro ao extrair CNPJ do certificado")
        return None


def extract_common_name(cert) -> Optional[str]:
    """
    Extrai o Common Name (CN) do certificado
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        String com o Common Name ou None se não encontrado
    """
    try:
        subject = cert.subject
        for attribute in subject:
            if attribute.oid.dotted_string == "2.5.4.3":  # Common Name
                return attribute.value
        return None
    except Exception:
        logger.exception("Erro ao extrair Common Name do certificado")
        return None


def extract_organization_name(cert) -> Optional[str]:
    """
    Extrai o nome da organização do certificado
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        String com o nome da organização ou None se não encontrado
    """
    try:
        subject = cert.subject
        for attribute in subject:
            if attribute.oid.dotted_string == "2.5.4.10":  # Organization Name
                return attribute.value
        return None
    except Exception:
        logger.exception("Erro ao extrair nome da organização do certificado")
        return None


def extract_policy_level(cert) -> Optional[str]:
    """
    Extrai o nível de política do certificado (A1, A3, etc.)
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        String com o nível de política ou None se não encontrado
    """
    try:
        for extension in cert.extensions:
            if extension.oid.dotted_string == "2.5.29.32":  # Certificate Policies
                policies = extension.value
                for policy in policies:
                    policy_oid = policy.policy_identifier.dotted_string
                    
                    # Verificar prefixos de política específicos
                    if policy_oid.startswith("2.16.76.1.2.1"):
                        return "A1"
                    elif policy_oid.startswith("2.16.76.1.2.3"):
                        return "A3"
                    elif policy_oid.startswith("2.16.76.1.2.4"):
                        return "A4"
        
        return None
        
    except Exception:
        logger.exception("Erro ao extrair nível de política do certificado")
        return None


def verify_brazilian_signature(signature, certification_path=None) -> Dict[str, Any]:
    """
    Verifica se a assinatura é válida para ICP-Brasil
    
    Args:
        signature: Informações da assinatura
        certification_path: Opcional, caminho da cadeia de certificação
    
    Returns:
        Dicionário com resultado da verificação
    """
    result = {
        "is_valid": False,
        "is_icp_brasil": False,
        "details": {}
    }
    
    try:
        # Verificar se tem certificado
        if not signature.get('certificate'):
            result["details"]["error"] = "Certificado não encontrado na assinatura"
            return result
            
        certificate = signature.get('certificate')
        
        # Verificar se é um certificado ICP-Brasil
        is_icp_brasil = check_if_icp_brasil(certificate)
        result["is_icp_brasil"] = is_icp_brasil
        result["details"]["certificate_info"] = extract_icp_brasil_info(certificate)
        
        # Verificar validade do certificado
        if datetime.now() > certificate.not_valid_after or datetime.now() < certificate.not_valid_before:
            result["details"]["certificate_validity"] = "Certificado fora da validade"
            return result
            
        # Verificar se o certificado está revogado (precisaria de uma consulta à LCR ou OCSP)
        # Implementação simplificada aqui
        revocation_check = {"status": "Não verificado", "is_revoked": False}
        result["details"]["revocation_check"] = revocation_check
        
        # Se chegou aqui e é ICP-Brasil, consideramos válido para fins de demonstração
        if is_icp_brasil:
            result["is_valid"] = True
            result["details"]["validation_status"] = "Certificado ICP-Brasil válido"
        else:
            result["details"]["validation_status"] = "Certificado não pertence à ICP-Brasil"
            
        return result
        
    except Exception as e:
        result["details"]["error"] = f"Erro na validação ICP-Brasil: {str(e)}"
        return result