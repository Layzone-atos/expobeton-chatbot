content = open('web/chat-widget.js', encoding='utf-8').read()
print('Has country field:', 'country: formData.get' in content)
print('Has country analytics:', "chatState.userInfo.country" in content)
