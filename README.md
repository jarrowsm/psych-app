# A no-framework pseudo-psychometric Web application
_Submitted in fulfilment of a university assignment. Some details are omitted to deter future students._

## Task
Develop a no-framework Web application for an online psychological profile.
After completing a psychometric questionnaire, selecting a job category and favourite animals, the application provides
a job suitability score, recommends films, and displays random images of the selected animals.

### Requirements
- Basic HTTP authentication
- Single-page application
- Consumes the following RESTful Web services:
  - [OMDb](http://www.omdbapi.com/) for movie information
  - [dog.ceo](https://dog.ceo/), [thecatapi](https://thecatapi.com/) and [random-d](https://random-d.uk/) for animal pictures

## Instructions
Pull the image from GHCR and run the server (e.g. on port 8001):
```shell
docker pull ghcr.io/jarrowsm/psychapp:latest
docker run -it -p 8001:8080 ghcr.io/jarrowsm/psychapp:latest
```
Username and password: `20005743`

A browser is recommended. Interacting via the command-line is also possible (e.g. via `curl` or `wget`).

## Stack
- python 3.13.3 (requests 2.32.3)
- Vanilla JS (ES2024) + CSS3
