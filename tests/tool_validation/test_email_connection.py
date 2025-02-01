
def test_get_email_body(gmail_imap_object):
    """Test that the IMAP service is working by retrieving the account activation email."""
    body = gmail_imap_object.get_last_email_by_subject("Se ha activado")
    assert "Si inicias sesión en un dispositivo nuevo o que no sea de confianza" in body