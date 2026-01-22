# Docs to static web site

## Principe :

- Récupérer les pages édité collaborativement sur DOCS ( https://docs.suite.anct.gouv.fr/home/ )
- Les stocker et les versionner en mardown via ce dépot Git
- Utiliser zensical pour les convertir en html 
- Uploader sur github/gitlab pages

## Exemple :

Sylvain Zimmer réalise la même chose pour via : https://docs.suite.anct.gouv.fr/docs/0b65cc5b-2d72-408a-b5c1-0ff8d2a7a479/
Mais avec une stack node js pour le fetch. Il récupère les fichier via le bouton "convertir en html" et le modifie automatiquement avec une lib https://github.com/rehypejs/rehype 

De notre coté, on préfère travailler en python et on veut bien tester Zensical pour voir ce qu'il a dans le bide :)