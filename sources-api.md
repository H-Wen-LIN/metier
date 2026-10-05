# Sources d'offres d'emploi en France — lesquelles ont une API ?

Recensement fait le 05/10/2026, pour savoir quels canaux on pourra brancher
plus tard sur le site, à côté de l'API France Travail déjà utilisée par
`scripts/extraire.py`. Liens vérifiés à cette date ; les conditions d'accès
(quotas, prix, contrat) changent souvent, à relire au moment de l'inscription.

## 1. Le recensement : tous les sites, avec ou sans API

« API » veut dire ici : une interface officielle qui permet à un site tiers
de **lire et afficher** des offres. Les API qui servent seulement aux
recruteurs à *publier* leurs annonces (multidiffusion depuis un ATS) ne
comptent pas.

| Site | Type | API de consultation des offres ? |
|---|---|---|
| France Travail (ex-Pôle emploi) | public, généraliste | ✅ ouverte à tous |
| La bonne alternance | public, alternance | ✅ ouverte à tous |
| API Engagement (Service civique, JeVeuxAider…) | public, missions d'engagement | ✅ sur demande |
| Apec | cadres | ❌ seulement l'API ADEP pour diffuser ses offres depuis un ATS |
| Place de l'emploi public / Choisir le service public | fonction publique | ❌ pas d'API directe (les offres sont relayées dans l'API France Travail) |
| Emploi-territorial, FHF (hospitalière) | fonction publique | ❌ |
| 1jeune1solution | public, jeunes | ❌ pas d'API propre (s'appuie sur France Travail et La bonne alternance) |
| Indeed | généraliste | ❌ programme Publisher fermé aux nouveaux partenaires depuis 2022 |
| LinkedIn | généraliste, réseau | ❌ API Job Posting réservée aux ATS partenaires, pas de recherche |
| HelloWork (ex-RegionsJob) | généraliste | ❌ API réservée aux recruteurs pour diffuser |
| Welcome to the Jungle | startups, cadres | ❌ |
| Monster | généraliste | ❌ |
| Meteojob | généraliste | ❌ |
| Cadremploi, Figaro Emploi, Keljob | cadres, généraliste | ❌ |
| Glassdoor | avis + offres | ❌ API fermée |
| Leboncoin Emploi | généraliste | ❌ |
| Qapa, StaffMe, Side | intérim, missions courtes | ❌ |
| JobTeaser | étudiants, jeunes diplômés | ❌ réservée aux écoles et partenaires |
| StudentJob, L'Étudiant, Studyrama | étudiants | ❌ |
| Free-Work, Malt, Crème de la Crème, Codeur.com | freelance | ❌ |
| Google for Jobs | moteur | ❌ (Cloud Talent Solution ne sert qu'à chercher dans *ses propres* offres) |
| Jobrapido | agrégateur | ❌ pas de programme public trouvé |
| Adzuna | agrégateur | ✅ inscription libre |
| Careerjet (Optioncarriere en France) | agrégateur | ✅ compte éditeur |
| Jooble | agrégateur | ✅ formulaire de demande de clé |
| Talent.com (ex-Neuvoo) | agrégateur | ✅ programme éditeurs, sur contrat |
| Jobijoba (groupe HelloWork) | agrégateur | ⚠️ API existante (client_id / secret), sans inscription en libre-service |

## 2. Les API retenues : gratuites et filtrables aussi finement que France Travail

Deux critères, tous deux obligatoires :

1. **Gratuite et en libre-service** : on crée un compte, on obtient la clé,
   sans contrat, sans paiement et sans avoir à faire valider un site éditeur.
2. **Filtrage précis côté API**, comme l'API Offres d'emploi v2 qu'utilise
   `scripts/extraire.py` : on demande un **code ROME** et un **territoire
   officiel** (département, commune), pas seulement des mots-clés à trier
   ensuite.

Deux API passent ces deux critères.

| API | Ce qu'on récupère | Créer le compte développeur | Documentation | Accès |
|---|---|---|---|---|
| **France Travail — Offres d'emploi v2** | Toutes les offres déposées à France Travail, plus celles des partenaires qui l'acceptent (dont la fonction publique) | [francetravail.io/inscription](https://francetravail.io/inscription), puis Mes applications → Créer une application → API « Offres d'emploi v2 » | [API Offres d'emploi v2](https://francetravail.io/data/api/offres-emploi) · [fiche data.gouv](https://www.data.gouv.fr/dataservices/api-offres-demploi) | Gratuit · OAuth2 (`client_id` / `client_secret`) · 10 appels/s · 150 offres par appel, 1 150 par requête. **Déjà branchée.** |
| **La bonne alternance — Job v1** | Offres en apprentissage et en contrat pro : France Travail, sites partenaires et offres déposées directement sur La bonne alternance | [api.apprentissage.beta.gouv.fr/fr/compte](https://api.apprentissage.beta.gouv.fr/fr/compte) (la clé se génère depuis le compte) | [Documentation technique](https://api.apprentissage.beta.gouv.fr/fr/documentation-technique) · [code et spec OpenAPI](https://github.com/mission-apprentissage/api-apprentissage) | Gratuit · clé API · `GET /job/v1/search`, et `GET /job/v1/export` pour tout télécharger d'un coup |

### Ce qu'on peut filtrer

| Filtre | France Travail — Offres d'emploi v2 | La bonne alternance — `/job/v1/search` |
|---|---|---|
| Métier | `codeROME` (plusieurs codes possibles), `appellation`, `motsCles` | `romes` (plusieurs codes), `rncp` (diplôme visé) |
| Territoire | `departement`, `region`, `commune` + `distance` | `departements`, ou `latitude` + `longitude` + `radius` |
| Contrat | `typeContrat` (CDI, CDD, MIS…), `natureContrat`, `tempsPlein`, `dureeHebdo` | alternance uniquement |
| Profil demandé | `experience`, `qualification`, `niveauFormation`, `permis` | `target_diploma_level` (niveaux 3 à 7) |
| Salaire | `salaireMin` + `periodeSalaire` | — |
| Employeur | `secteurActivite`, `codeNAF`, `entreprisesAdaptees` | `opco` |
| Fraîcheur | `publieeDepuis` (1, 3, 7, 14, 31 jours), `minCreationDate` / `maxCreationDate` | — |
| Origine | `origineOffre`, `partenaires` + `modeSelectionPartenaires` | `partners_to_exclude` |

Pour nos 23 codes ROME, La bonne alternance s'interroge donc exactement comme
France Travail : `romes=M1718,M1716,…`. Elle reprend une partie des offres
d'alternance de France Travail : passer celles-ci dans `partners_to_exclude`
pour ne pas les compter deux fois.

### Écartées à ce tri

| API | Gratuite ? | Pourquoi elle sort |
|---|---|---|
| Adzuna | ✅ avec quota | Filtrage par mots-clés (`what`, `what_exclude`), lieu en texte (`where`), catégories maison, `permanent` / `contract`, `salary_min`, `max_days_old` : pas de code ROME ni de code INSEE. La plus proche : à reprendre si l'on accepte une requête par mots-clés |
| Careerjet / Optioncarriere | ✅ rémunérée au clic | Mots-clés, lieu en texte, type de contrat seulement ; il faut un site éditeur et transmettre l'IP et le user-agent de chaque visiteur |
| Jooble | ⚠️ clé après validation, quota gratuit très faible | Mots-clés et lieu seulement |
| Talent.com, Jobijoba | ❌ sur contrat ou sur demande | Pas d'inscription en libre-service |
| API Engagement | ✅ sur demande | Missions de Service civique et de bénévolat, pas des emplois |
| The Muse, Remotive, Himalayas, Arbeitnow | ✅ | Peu d'offres françaises, pas de filtre par département |
| ATS (SmartRecruiters, Lever, Greenhouse…) | ✅ | Une entreprise à la fois, pas le marché |

## 3. Ce qu'il faut savoir avant de brancher une deuxième source

- **Doublons.** La bonne alternance reprend une partie des offres de France
  Travail : exclure ce partenaire dans la requête, puis garder une empreinte
  (intitulé + entreprise + commune) en filet de sécurité, comme on le fait
  déjà pour le réseau M1716.
- **Une source, une colonne.** Garder `source` dans les données brutes
  (`data/brut/`) pour que chaque chiffre du site dise d'où il vient.
- **Si l'on rouvre un jour aux agrégateurs** (Adzuna en tête) : pas de code
  ROME, donc une requête par mots-clés qui ramène du bruit (voir le README :
  424 offres pour « marketing digital » contre 113 en M1718), et des CGU qui
  exigent en général un lien vers leur site et la citation de la source.
- **Identifiants.** Comme pour France Travail : dans `.env` en local, dans les
  secrets du dépôt sur GitHub, jamais dans un fichier versionné.
- **Toujours pas de scraping** de LinkedIn, de l'Apec, d'Indeed ni des sites
  sans API : c'est interdit par leurs CGU.
