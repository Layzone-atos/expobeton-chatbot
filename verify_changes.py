import sys
c1 = open('chatbot-admin/conversation_detail.php', encoding='utf-8').read()
c2 = open('chatbot-admin/conversations.php', encoding='utf-8').read()
c3 = open('chatbot-admin/config.php', encoding='utf-8').read()
print('detail has formatCountryWithFlag:', 'formatCountryWithFlag' in c1)
print('conversations has formatCountryWithFlag:', 'formatCountryWithFlag' in c2)
print('config has getCountryFlag:', 'getCountryFlag' in c3)
print('config has formatCountryWithFlag:', 'formatCountryWithFlag' in c3)
