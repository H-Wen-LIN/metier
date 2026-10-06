# Grille de codage — 120 offres D1415

Vous lisez, pour chaque offre de `echantillon.csv`, l'**intitulé** et la **description**, et rien d'autre. Pour chacune des quatre variables, vous notez **1** ou **0**. Si vous hésitez, vous choisissez quand même, puis vous mettez `doute = 1` et vous expliquez en une phrase dans `note`.

Règle générale : on code **ce que l'offre dit du poste**, pas ce qu'on devine du secteur. Un mot présent ne suffit pas : il faut qu'il concerne le poste proposé.

## 1. `teletravail`

**1** si l'offre indique que le titulaire du poste **peut travailler à distance**, quel qu'en soit le volume ou la condition : « télétravail 2 jours par semaine », « hybride », « télétravail possible après la période d'essai », « full remote », « télétravail occasionnel ».

**0** :
- rien n'est dit ;
- le télétravail est exclu (« poste 100 % sur site », « pas de télétravail ») ;
- le mot apparaît sans concerner le poste (« nous équipons les entreprises pour le télétravail »).

## 2. `langue_etrangere`

**1** si une langue **autre que le français** est exigée, souhaitée ou présentée comme un atout **pour le poste** : « anglais courant exigé », « l'anglais serait un plus », « bilingue français-espagnol », « vous traiterez des clients germanophones en allemand ».

**0** :
- aucune langue étrangère ;
- seul le français est demandé ;
- la langue n'apparaît que dans un nom propre, un nom d'entreprise, d'école ou de produit, ou sans lien avec le travail.

## 3. `orientation_commerciale`

**1** si les missions du poste comportent **explicitement de la vente ou un objectif commercial** :
- vendre des produits ou des services, conclure des ventes ;
- prospecter de nouveaux clients ;
- appels sortants de vente, télévente ;
- vente additionnelle, montée en gamme, *upsell* ou *cross-sell* ;
- objectifs commerciaux, de vente ou de chiffre d'affaires ;
- rémunération liée aux ventes réalisées.

**0** si le poste est un poste de **service ou de relation sans vente explicite** :
- accueil, information, orientation ;
- traitement des demandes, réclamations, service après-vente ;
- suivi de dossiers, administration des ventes, recouvrement ;
- « fidéliser la clientèle » ou « développer la relation client » sans mention d'une vente ou d'un objectif commercial.

Un poste de **conseiller de vente** (en magasin ou à distance) est codé 1.

## 4. `horaires_atypiques`

**1** si l'emploi du temps **du titulaire du poste** comprend le **samedi, le dimanche, le week-end ou les jours fériés**, régulièrement ou par roulement : « travail un samedi sur deux », « du lundi au samedi », « planning incluant les week-ends », « permanences le samedi matin ».

**0** :
- horaires du lundi au vendredi, ou rien n'est dit ;
- le week-end est mentionné comme jour de repos (« week-ends libres », « pas de travail le dimanche ») ;
- le week-end est mentionné sans rapport avec l'emploi du temps du poste (« le magasin organise un événement le week-end »).

## Format de sortie

Un fichier CSV (séparateur virgule, encodage UTF-8), une ligne par offre, dans l'ordre de `num` :

```
num,id,teletravail,langue_etrangere,orientation_commerciale,horaires_atypiques,doute,note
```

- `teletravail` … `horaires_atypiques` : 0 ou 1.
- `doute` : 1 si au moins une des quatre variables vous a fait hésiter, sinon 0.
- `note` : vide, ou une phrase courte. Pour chaque variable codée 1, donnez l'extrait de l'offre qui le justifie, entre guillemets, en moins de 15 mots. Pensez à mettre le champ entre guillemets doubles s'il contient des virgules.

---

## Précision ajoutée après le double codage du 06/10/2026

*Les deux codeurs n'ont pas eu cette section. Elle fixe la règle appliquée pour départager leurs 9 désaccords sur `orientation_commerciale` (voir `../arbitrage.csv`). Elle vaut pour tout codage ultérieur.*

- `orientation_commerciale` = **1** quand le poste **génère ou convertit lui-même des ventes** : négocier des conditions commerciales, relancer des devis ou des offres, développer l'activité commerciale, travailler des prospects, vendre.
- `orientation_commerciale` = **0** quand le poste **traite** des demandes : établir un devis ou une offre à la demande, enregistrer des commandes, « proposer les produits et services adaptés » sans vente ni objectif nommés, participer « occasionnellement » à une négociation menée par un commercial.
- `horaires_atypiques` = **1** quand l'offre annonce plus de 5 jours travaillés par semaine (« 35 h sur 6 jours ») : un jour du week-end en fait forcément partie.
