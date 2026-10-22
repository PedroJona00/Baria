class ResponseValidator:
    def validate(self, result, kb, allowed_ids=None):
        message = result.get('message')
        if not isinstance(message, str) or not message.strip(): raise ValueError('Resposta vazia')
        if len(message) > 12000: result['message'] = message[:11900] + '\nConsulte o painel para mais informações.'
        if 'drink' in result:
            identity = result['drink']['id']
            if identity not in kb.by_id or result['drink'] != kb.by_id[identity]: raise ValueError('Bebida sem base de conhecimento')
            if allowed_ids is not None and identity not in allowed_ids: raise ValueError('Recomendação viola filtros')
        return result
