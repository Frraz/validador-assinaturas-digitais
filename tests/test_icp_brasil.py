import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.validation.icp_brasil import (
    check_if_icp_brasil,
    extract_icp_brasil_info,
    extract_cpf_from_certificate,
    extract_cnpj_from_certificate
)

class TestIcpBrasil(unittest.TestCase):
    """Testes para o módulo de validação ICP-Brasil"""
    
    def setUp(self):
        """Configuração para testes"""
        # Criar mock de certificado
        self.mock_cert = MagicMock()
        self.mock_cert.not_valid_before = datetime.now() - timedelta(days=365)
        self.mock_cert.not_valid_after = datetime.now() + timedelta(days=365)
        self.mock_cert.serial_number = 12345
        self.mock_cert.issuer = MagicMock()
        self.mock_cert.issuer.__str__ = lambda _: "CN=Autoridade Certificadora Raiz Brasileira, OU=Instituto Nacional de Tecnologia da Informacao - ITI, O=ICP-Brasil, C=BR"
        self.mock_cert.subject = MagicMock()
        self.mock_cert.subject.__str__ = lambda _: "CN=JOAO SILVA:12345678909, OU=Certificado PF A3, O=ICP-Brasil, C=BR"
        
        # Configurar extensões para simular certificado ICP-Brasil
        mock_extension1 = MagicMock()
        mock_extension1.oid.dotted_string = "2.16.76.1.2.1.1"
        mock_extension1.value = MagicMock()
        
        mock_extension2 = MagicMock()
        mock_extension2.oid.dotted_string = "2.5.29.32"  # Certificate Policies
        policy_mock = MagicMock()
        policy_mock.policy_identifier.dotted_string = "2.16.76.1.2.3.1"  # ICP-Brasil A3 PF
        mock_extension2.value = [policy_mock]
        
        self.mock_cert.extensions = [mock_extension1, mock_extension2]
    
    def test_check_if_icp_brasil(self):
        """Testa detecção de certificado ICP-Brasil"""
        self.assertTrue(check_if_icp_brasil(self.mock_cert))
        
        # Testar com certificado não ICP-Brasil
        non_icp_cert = MagicMock()
        non_icp_cert.issuer.__str__ = lambda _: "CN=Some CA, O=Some Organization, C=US"
        non_icp_cert.extensions = []
        self.assertFalse(check_if_icp_brasil(non_icp_cert))
    
    def test_extract_icp_brasil_info(self):
        """Testa extração de informações de certificado ICP-Brasil"""
        with patch('app.validation.icp_brasil.check_if_icp_brasil') as mock_check:
            mock_check.return_value = True
            
            with patch('app.validation.icp_brasil.detect_certificate_type') as mock_detect:
                mock_detect.return_value = "A3 - Pessoa Física"
                
                with patch('app.validation.icp_brasil.extract_cpf_from_certificate') as mock_cpf:
                    mock_cpf.return_value = "123.456.789-09"
                    
                    with patch('app.validation.icp_brasil.extract_common_name') as mock_cn:
                        mock_cn.return_value = "JOAO SILVA"
                        
                        info = extract_icp_brasil_info(self.mock_cert)
                        
                        self.assertTrue(info["is_icp_brasil"])
                        self.assertEqual("A3 - Pessoa Física", info["certificate_type"])
                        self.assertEqual("123.456.789-09", info["person_info"]["cpf"])
                        self.assertEqual("JOAO SILVA", info["person_info"]["name"])
    
    def test_extract_cpf_from_certificate(self):
        """Testa extração de CPF de certificado"""
        with patch('app.validation.icp_brasil.re.search') as mock_search:
            mock_match = MagicMock()
            mock_match.group.return_value = "123.456.789-09"
            mock_search.return_value = mock_match
            
            # Configurar uma extensão com OID de pessoa física
            cpf_extension = MagicMock()
            cpf_extension.oid.dotted_string = "2.16.76.1.3.1"
            cpf_value_mock = MagicMock()
            cpf_value_mock.value = b"12345678909"
            cpf_extension.value = cpf_value_mock
            
            cert_with_cpf = MagicMock()
            cert_with_cpf.extensions = [cpf_extension]
            
            cpf = extract_cpf_from_certificate(cert_with_cpf)
            self.assertIsNotNone(cpf)
    
    def test_extract_cnpj_from_certificate(self):
        """Testa extração de CNPJ de certificado"""
        with patch('app.validation.icp_brasil.re.search') as mock_search:
            mock_match = MagicMock()
            mock_match.group.return_value = "12.345.678/0001-99"
            mock_search.return_value = mock_match
            
            # Configurar certificado com informação de CNPJ no subject
            cert_with_cnpj = MagicMock()
            cert_with_cnpj.subject.__str__ = lambda _: "CN=EMPRESA LTDA:12345678000199, OU=Certificado PJ A1, O=ICP-Brasil, C=BR"
            cert_with_cnpj.extensions = []
            
            cnpj = extract_cnpj_from_certificate(cert_with_cnpj)
            self.assertIsNotNone(cnpj)


if __name__ == '__main__':
    unittest.main()