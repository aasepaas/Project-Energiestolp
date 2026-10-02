Ontwerp in C4-model:

Het C4-model staat volledig in deze map:

- `ses_v0.1_en.c4`: het model, niveau 1 tot en met 3
- `likec4.config.json`: maakt van deze map het LikeC4-project "Smart Energie Stolp"
- `.likec4/`: handmatig aangepaste layouts van views (`<view-id>.likec4.snap`)

Ontwerp kan in de terminal gestart worden met de volgende commando (vanuit de root of vanuit deze map):
npx likec4 start

hiervoor is de extension likec4 in Visual Studio Code nodig.

Views:

- `index`: 1 - Context
- `ses`: 2 - Containers
- `webappDetail`, `ingestDetail`, `databaseDetail`, `rekenDetail`, `backendApiDetail`, `frontendApiDetail`, `mlComponents`: 3.1 tot en met 3.7, componenten per container
- `componenten`: 3 - Componenten, alle componenten in één view

context niveau:
<img width="1406" height="628" alt="index" src="https://github.com/user-attachments/assets/6afe30b4-45c3-47d1-8ec8-5931794f611b" />

Component niveau:
<img width="2047" height="1425" alt="saas" src="https://github.com/user-attachments/assets/b9c4b80e-bf55-4d4c-93d4-d4fcc3119346" />
