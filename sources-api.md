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

## 2. Les sites retenus : ceux qui donnent une API

Classés du plus simple au plus contraignant à obtenir.

| Site | Ce qu'on récupère | Créer le compte développeur | Documentation | Accès et authentification | Points d'attention |
|---|---|---|---|---|---|
| **France Travail** | Toutes les offres déposées à France Travail + celles des partenaires qui l'acceptent (dont la fonction publique) | [francetravail.io/inscription](https://francetravail.io/inscription) | [API Offres d'emploi v2](https://francetravail.io/data/api/offres-emploi) · [fiche data.gouv](https://www.data.gouv.fr/dataservices/api-offres-demploi) | Gratuit · OAuth2 (`client_id` / `client_secret`) · 10 appels/s | **Déjà branchée.** 150 offres par appel, 1 150 par requête |
| **La bonne alternance** | Offres en apprentissage et contrat pro (France Travail, partenaires, offres déposées directement), formations | [api.apprentissage.beta.gouv.fr/fr/compte](https://api.apprentissage.beta.gouv.fr/fr/compte) | [Documentation technique](https://api.apprentissage.beta.gouv.fr/fr/documentation-technique) · [fiche data.gouv](https://www.data.gouv.fr/dataservices/api-la-bonne-alternance) | Gratuit · jeton API créé depuis son compte | Recoupe en partie France Travail : dédoublonner |
| **Adzuna** | Agrégat multi-sites, France incluse (`/v1/api/jobs/fr/search`), salaires estimés | [developer.adzuna.com/signup](https://developer.adzuna.com/signup) | [developer.adzuna.com](https://developer.adzuna.com/) | Gratuit avec quota · `app_id` + `app_key` | Clés immédiates ; les liens renvoient vers Adzuna |
| **Careerjet / Optioncarriere** | Agrégat multi-sites (`locale_code=fr_FR`) | [Créer un compte éditeur](https://www.careerjet.com/partners/register/as-publisher) | [API v4](https://www.careerjet.com/partners/api) | Gratuit, rémunéré au clic · clé API en Basic Auth | Une clé par site éditeur ; il faut transmettre l'IP et le user-agent du visiteur |
| **Jooble** | Agrégat multi-sites | [fr.jooble.org/api/about](https://fr.jooble.org/api/about) (formulaire) | [Documentation REST](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation) | Clé envoyée après validation · `POST` JSON | Une clé **par pays** : la demander sur le domaine `fr.` ; quota gratuit faible |
| **Talent.com** | Agrégat multi-sites, 70+ pays | [Programme éditeurs](https://employers.talent.com/publishers) → [contact](https://www.talent.com/contact) | fournie après accord | Contrat éditeur, rémunéré au clic · API ou flux XML | Pas d'inscription en libre-service : il faut un site avec de l'audience |
| **Jobijoba** | Agrégat d'environ 400 sites emploi | [Formulaire de contact](https://www.jobijoba.com/fr/contact) | fournie après accord | `client_id` / `client_secret` | API non documentée publiquement : à demander |

### À la marge

Utiles pour un complément, mais pas des sites emploi français.

| Source | Pourquoi à la marge | Créer le compte | Documentation |
|---|---|---|---|
| API Engagement | Missions de Service civique et de bénévolat, pas des emplois | [app.api-engagement.beta.gouv.fr](https://app.api-engagement.beta.gouv.fr/) (sur demande à l'équipe) | [doc.api-engagement.beta.gouv.fr](https://doc.api-engagement.beta.gouv.fr/) |
| The Muse | Surtout des offres américaines, quelques-unes à Paris | [Enregistrer une application](https://www.themuse.com/developers/api/v2/apps) (clé facultative, elle relève le quota) | [API v2](https://www.themuse.com/developers/api/v2) |
| Remotive, Himalayas, Arbeitnow | Télétravail ou Europe, peu d'offres françaises | aucun compte nécessaire | [Remotive](https://remotive.com/remote-jobs/api) · [Himalayas](https://himalayas.app/api) · [Arbeitnow](https://www.arbeitnow.com/blog/job-board-api) |
| ATS : SmartRecruiters, Lever, Greenhouse, Teamtailor | Page carrière d'une entreprise précise, pas tout le marché | aucun compte pour lire les offres publiées | [SmartRecruiters Posting API](https://developers.smartrecruiters.com/docs/posting-api) |

## 3. Ce qu'il faut savoir avant de brancher une deuxième source

- **Doublons.** Les agrégateurs (Adzuna, Careerjet, Jooble, Talent.com,
  Jobijoba) reprennent en grande partie les mêmes annonces, dont celles de
  France Travail. Il faudra une empreinte (intitulé + entreprise + commune)
  pour ne pas compter deux fois la même offre, comme on le fait déjà pour le
  réseau M1716.
- **Pas de code ROME chez les agrégateurs.** On cherche par mots-clés, ce qui
  ramène du bruit (voir le README : 424 offres pour « marketing digital »
  contre 113 en M1718). Garder France Travail comme référence et afficher les
  autres sources à part.
- **Conditions d'affichage.** Les programmes éditeurs (Careerjet, Jooble,
  Talent.com, Adzuna) exigent en général que l'offre renvoie vers leur site
  et que la source soit citée. Ils sont pensés pour un site public avec de
  l'audience, pas pour une archive de données : lire les CGU avant de
  conserver le brut comme on le fait pour France Travail.
- **Identifiants.** Comme pour France Travail : dans `.env` en local, dans les
  secrets du dépôt sur GitHub, jamais dans un fichier versionné.
- **Toujours pas de scraping** de LinkedIn, de l'Apec, d'Indeed ni des sites
  sans API : c'est interdit par leurs CGU.
