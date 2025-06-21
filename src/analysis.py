"""
Performs analysis to the assignment specifications. Please refer to the report for the
methodologies used. Any ValueError is caught by do_analyse and sends a 500 response.
"""

import os
import glob
import json

from response_utils import send_response
from fetch_utils import fetch_data, check_img, download_img

os.environ["OMDb_API_KEY"] = "2c9b7593"


class PsychProfiler:
    """ Psychological evaluation class """
    def __init__(self, form_input: dict[str], max_score: int = 5):
        self.form_input = form_input
        self.max_score = max_score
        self.setup()

    def setup(self) -> None:
        with open('weights.json', 'r') as f:
            weights = json.load(f)

        # Contains the job weights (see report) and a relevant
        # film (title, year)
        self.job_dict = weights['jobs']
        self.set_job(self.form_input['job'])

        # Derived from the MOVIE framework (Monteiro and Pimentel, 2023)
        # For films, I use the example from the study for the most
        # correlated genre within a preference category
        self.movie_dict = weights['movies']

        # Each question is mapped to one of the Big Five traits
        trait_map_temp = {
            'O':[3,7,11],
            'C':[2,5,10,12,15],
            'E':[1,8,14,16,20],
            'A':[4,9,17,18],
            'N':[6,13,19]
        }
        self.trait_map = {}
        for k, vs in trait_map_temp.items():
            for v in vs:
                self.trait_map[v] = k

        # Account for reversed questions
        self.reversed_qns = [5,6,9,12,14,16,17,18]

    def normalise_scores(self,
                         scores: list[float],
                         total_possible_min: float,
                         total_possible_max: float) -> float:
        # Given a list of weighted scores, returns a final score normalised
        # to the range [0, max_score]. Modifying max_score will adjust
        # everything accordingly
        raw_sum = sum(scores)

        normalised_score = self.max_score * ((raw_sum - total_possible_min) / 
                                            (total_possible_max - total_possible_min))
        
        return max(0, min(normalised_score, self.max_score))
    
    def analyse(self) -> dict:
        # Analyse psychological form data for job suitability and 
        # movie recommendation. Returns a dict which also includes
        # the career-based movie recommendation

        weighted_job_scores = []
        weighted_movie_scores = { k : {'scores': [], 'min': []}
                                  for k in self.movie_dict.keys() }

        min_job_scores = []

        for k, v in self.form_input.items():
            if k.startswith('question'):
                q, a = int(k[len('question'):]), int(v)

                if q in self.reversed_qns:
                    a = 6 - a  # Reverse Likert scale value

                a-=3  # Shift to range [-2,...,2]

                # Apply weight
                trait = self.trait_map[q]
                w = self.job_info['weights'][trait]
                weighted_job_scores.append(a * w)

                # Worst-case: 5 for -ve weight, 1 for +ve weight
                min_job_scores.append(w * 2 if w < 0 else w * -2)
                
                # Apply weight for actual & worst for each psych movie
                for k_, v_ in self.movie_dict.items():
                    w_ = v_['weights'][trait]
                    weighted_movie_scores[k_]['scores'].append(a * w_)
                    weighted_movie_scores[k_]['min'].append(
                        w_ * 2 if w_ < 0 else w_ * -2)

        total_min = sum(min_job_scores)
        total_max = -total_min  # since response range is {-2,...,2}
        self.job_score = self.normalise_scores(
            weighted_job_scores, total_min, total_max)

        # All neutral responses -> every film gets max_score/2
        # Hence, set a default: LotR ('I')
        self.psych_movie = self.movie_dict['I']

        # Find the most suitable psych movie
        # Need the score - similar to above - for each
        movie_score = self.max_score / 2
        for k, s in weighted_movie_scores.items():
            total_min = sum(s['min'])
            total_max = -total_min
            s = self.normalise_scores(
                s['scores'], total_min, total_max)
            if s > movie_score:
                movie_score = s
                self.psych_movie = self.movie_dict[k]
        self.psych_movie['suitability'] = movie_score

        return {
            'career': {
                'desired': self.job,
                'suitability': self.job_score,
            },
            'movies': {
                'job': self.job_info['movie'],
                'psych': self.psych_movie,
            },
            'max_score': self.max_score,
        }

    def set_job(self, job: str) -> None:
        jobs = ['ceo', 'astronaut', 'doctor', 'model', 'rockstar', 'garbage']

        if job not in jobs:
            raise ValueError(f'job must be in {jobs}')

        self.job = job
        self.job_info = self.job_dict[job]


class DataFetcher:
    """
        Fetch relevant data (movies and pets) from the
        third party sites via their RESTful API
    """

    def __init__(self):
        omdb_key = os.environ.get("OMDb_API_KEY")
        self.apis = {
            'dog': 'https://dog.ceo/api/breeds/image/random',
            'cat': 'https://api.thecatapi.com/v1/images/search',
            'duck': 'https://random-d.uk/api/v2/random',
            'movie': f'http://www.omdbapi.com/?apikey={omdb_key}'
        }

    def fetch_pet_img_ref(self, pet: str) -> str:
        # Fetch pet image metadata

        if pet not in ['dog', 'cat', 'duck']:
            raise ValueError('pet must be `dog`, `cat` or `duck`')
        
        uri = self.apis[pet]

        # Ensure image is JPG/JPEG/GIF/PNG
        valid = False
        while not valid:
            response = fetch_data(uri)

            # Action each of the URLs referenced in the first response
            # Since only one image is fetched, the message is the URL
            # Some APIs use 'url', while others use 'message'
            response = response[0] if isinstance(response, list) else response
            img_url = response.get('url', response.get('message'))
            valid = check_img(img_url)

        return img_url

    def fetch_movie_data(self,
                         movie_info: dict[str],
                         download_posters: bool = True) -> dict[str]:
        # Fetch the movie data from OMDb. Search includes both
        # title and year as this ensures that the film is correct.
        # Returns a dictionary derived from the JSON response.

        t = movie_info['title'].replace(' ', '+')
        y = movie_info['year']
        uri = f"{self.apis['movie']}&t={t}&y={y}"
        movie_data = fetch_data(uri)
        movie_data.pop('Response')
        movie_data['local_poster'] = (
            download_img(movie_data['Poster']) if download_posters
            else None
        )

        return movie_data

    def clear_images(self):
        # Helper method to delete local images. Not used in the final
        # version since images were not removed in the tutorial demo
        for fp in glob.glob(f'images/*'):
            if os.path.isfile(fp):
                print(f'Removing {fp}') 
                os.remove(fp)

    def download_pet_images(self, pets: str | list) -> dict[str]:
        # Downloads images for each pet and returns the local references

        if isinstance(pets, str):
            pets = [pets]

        local_uris = {}
        for pet in pets:
            url = self.fetch_pet_img_ref(pet)
            local_uris[pet] = download_img(url)

        return local_uris


def analyse(input_path: str = os.path.join('data', 'input.json'),
            quiet: bool = True) -> dict:
    # This function utilises PsychProfiler and DataFetcher to
    # form a profile to the assignment specifications

    if not os.path.exists(input_path):
        raise ValueError(f'Missing {input_path}')

    with open(input_path, 'r') as f:
        form_input = json.load(f)

    profiler = PsychProfiler(form_input)
    data_fetcher = DataFetcher()

    # Create the psychological profile
    profile = profiler.analyse()

    # Fetch movie data for job & psych recommendations
    movie_suitability = profile['movies']['psych']['suitability']
    for k, v in profile['movies'].items():
        profile['movies'][k] = data_fetcher.fetch_movie_data(v)
    profile['movies']['psych']['suitability'] = movie_suitability

    # Fetch pet images
    profile['pets'] = data_fetcher.download_pet_images(form_input['pets'])

    # Copy name for greeting
    profile['name'] = form_input['name'].title()

    # Add a tag to avoid re-analysing
    form_input['analysed'] = True

    # Save the serialised profile
    input_path = os.path.join('data', 'input.json')
    profile_path = os.path.join('data', 'profile.json')
    with open(input_path, 'w') as f:
        json.dump(form_input, f)
    with open(profile_path, 'w') as f:
        json.dump(profile, f)

    if not quiet:
        print('Generated profile:', profile)

    return profile

