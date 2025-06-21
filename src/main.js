/*
 * The website is a single-page application (SPA): either the index or 404 (or 403) pages
 * as entry points. This script actions the URIs according to the brief, and displays the
 * content appropriately. Also, while the website is intended for the browser, command-line
 * clients (e.g., curl and wget) are supported as well.
 */


// Displays text (including errors)
async function writeMsg(msg) {
    // Create container with message
    msgDiv = document.createElement('div');
    msgDiv.className = 'message-container';
    msgDiv.textContent = msg;

    // Insert into the DOM
    const container = document.getElementById('mydiv1');
    container.innerHTML = '';
    container.appendChild(msgDiv);
}


// Retrieve HTML or JSON content using GET or POST via fetch
// to facilitate SPA functionality.
async function fetchData(uripath, method = "GET", data = null) {
    try {
        // Send the request
        let response;

        if (method === "GET") {
            response = await fetch(uripath);
        } else if (method === "POST") {
            const postData = {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            };
            response = await fetch(uripath, postData);
        } else throw new Error("Only `GET` and `POST` requests are supported.");

        // Handle the HTML/JSON response
        const contentType = response.headers.get("Content-Type");
        let responseData;

        if (contentType && contentType === "application/json") {
            responseData = await response.json();
        } else responseData = await response.text();  // HTML
      
        if (!response.ok) { 
            await writeMsg(responseData.message);
            return null;
        }

        // Return payload of 200 response 
        return responseData;

    } catch (e) {
        console.error("Error fetching data:", e);
        return null;
    }
}


// Called by the logo or Return Home in 404.html
async function returnHome() {
    document.documentElement.innerHTML = await fetchData('/');
}


// Inserts a convenient Go to Top button for long pages
async function insertScrollButton(parentID) {
    const button = document.createElement('button');
    button.className = 'scroll-button';
    button.textContent = 'Go to Top';
    button.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    document.getElementById(parentID).appendChild(button);
}


// Reset a button and its content
async function resetButton(buttonName) {
    const buttonMap = {
        viewForm: ['view-form', 'View Form', fetchForm],
        viewInput: ['view-input', 'Review', viewInput], 
        viewProfile: ['view-profile', 'View Profile', viewProfile]
    };
    const [id, text, fn] = buttonMap[buttonName];
    const button = document.getElementById(id);
    if (button.textContent !== text) {
        button.textContent = text;
        button.onclick = fn;
        document.getElementById('mydiv1').innerHTML = '';
    }
}


// Iteratively reset all activated buttons
async function resetAllButtons(
    buttons = ['viewForm', 'viewInput', 'viewProfile']
) { for (const btn of buttons) await resetButton(btn); }


// Activate a button
async function activateButton(buttonName) {
    const buttonMap = {
        viewForm: ['view-form', 'Close Form'],
        viewInput: ['view-input', 'Close Review'], 
        viewProfile: ['view-profile', 'Close Profile']
    };
    const [id, text] = buttonMap[buttonName];
    const button = document.getElementById(id);
    button.textContent = text;
    button.onclick = () => resetButton(buttonName);
}


// Called by the View Form button
async function fetchForm() {
    await resetAllButtons();
    const form = await fetchData('/form');
    if (!form) return

    document.getElementById('mydiv1').innerHTML = form;
    await activateButton('viewForm');
    await insertScrollButton('mydiv1');
}


// Called by the Submit button and converts the form
// data into a JSON payload
async function submitForm() {
    const form = document.forms['psychoform'];
    await resetAllButtons();  // Must go after!

    let jsonData = 'repeat';

    if (form) {
        jsonData = {};
        // Initialise empty arrays for checkboxes
        for (const e of form.elements) {
            if (e.type === 'checkbox' && !jsonData[e.name]) {
                jsonData[e.name] = [];
            }
        }
        // Format JSON payload: append checkboxes and set others
        const formData = new FormData(form);
        for (const [k, v] of formData.entries()) {
            if (form.elements[k][0]?.type === 'checkbox') jsonData[k].push(v);
            else jsonData[k] = v;
        }
    }

    // `jsonData` is "repeat" if no form is in the DOM,
    // implying 'Submit' before 'View Form'.
    // This is handled by the server (400 response)
    const ok = await fetchData('/submit', "POST", jsonData);
    if (ok) await writeMsg(ok.message);  // Note: removes form from the DOM
}


// Called by the Analyse button
async function analyze() {
    await resetAllButtons();
    await writeMsg('Analysing...');  // (may take a few seconds)
    const ok = await fetchData('/analyze', "POST");
    if (ok) await writeMsg(ok.message);  // Send message only
}


// Displays input data stored in the server in a locked form
async function insertLockedForm(data) {
    const container = document.getElementById('mydiv1');
    const header = '<h2 class="view-header">Your Responses</h2>';

    // Ensure the form is in the DOM
    let form = document.forms['psychoform'];
    if (form) {
        container.innerHTML = header;
        container.appendChild(form);
    } else {
        // Need to fetch the form to fill in
        const formHTML = await fetchData('/form');
        if (formHTML) {
            container.innerHTML = header + formHTML;
            form = document.forms['psychoform'];
        } else throw new Error("Failed to load form");
    }

    // Change the form's name so it cannot be submitted again
    form.setAttribute('name', 'viewpsychoform');

    // Fill in the form with data stored on the server and lock it
    for (const k in data) {
        const field = form.elements.namedItem(k)
        if (field) {
            const v = data[k];
            const type = field?.type || field[0]?.type;
            if (type !== 'checkbox') field.value = v;
            switch (type) {
                case 'radio':
                case 'checkbox': 
                    // Individual elements: set (checkbox), lock (radio & checkbox)
                    for (const e of field) {
                        if (type === 'checkbox' && v.includes(e.value)) {
                            e.checked = true;
                        }
                        e.disabled = true;
                    }
                    break;
                default:
                    field.disabled = true; break;
            }
        }
    }
}


// Called by the Review button
async function viewInput() {
    await resetAllButtons();

    let data = await fetchData('/view/input');
    if (!data) return;

    await insertLockedForm(data);

    await activateButton('viewInput');
    await insertScrollButton('mydiv1');
}


// Helper function returning a colour and statement based
// on the psychological results
function getColourVerdict(suitability, maxScore) {
    let colour, verdict;
    const perc = suitability / maxScore;

    if (perc < 0.33) {
        colour = 'red', verdict = 'Unlikely to be suitable';
    } else if (perc >= 0.66) {
        colour = 'green', verdict = 'Likely to be suitable';
    } else {
        colour = 'orange', verdict = 'Hard to tell';
        if (perc != .5) verdict += `, leaning towards
            ${perc < 0.5 ? 'un' : ''}suitable`;
    }

    return [colour, verdict];
}


// Formats and inserts the profile
async function insertProfile(data) {
    const jobMap = {
        ceo: 'CEO of a large mega-corporation',
        astronaut: 'Astronaut',
        doctor: 'Medical doctor',
        model: 'Fashion model',
        rockstar: 'Rock star',
        garbage: 'Refuse collection operative'
    };

    // Gather relevant data
    const jobStr = jobMap[data.career.desired];
    const jobScore = data.career.suitability.toFixed(1);
    const jobMovie = data.movies.job;
    const psychMovie = data.movies.psych;
    const movieScore = psychMovie.suitability.toFixed(1);
    const maxScore = data.max_score;
    const pets = data.pets;
    const name = data.name;

    // Generate colours and verdicts
    const [jobColour, jobVerdict] = getColourVerdict(jobScore, maxScore);
    const [movieColour, movieVerdict] = getColourVerdict(movieScore, maxScore);

    // Info box template
    const template = (info) => `
        <div class="info-container" id="${info.type}-container">
            <h2>${info.h2}</h2> ${info.p}
            <h4>Psychological Suitability</h4>
            <div id="${info.type}-suitability">
                <span>${info.score} / ${maxScore}</span>
            </div>
            <p><b>Outcome</b>: <i>${info.verdict}</i></p>
        </div>`;
      
    // Fill in the template for job suitability
    const jobContent = template({
        h2: "Career Information",
        p: `<p><b>You chose:</b> <i>${jobStr}</i></p>`,
        type: "job", score: jobScore, verdict: jobVerdict
    });

    // Create posters from images stored on the server
    const jobPoster = document.createElement('img');
    jobPoster.src = jobMovie.local_poster;
    jobPoster.alt = `Poster for ${jobMovie.Title}`;

    const psychPoster = document.createElement('img');
    psychPoster.src = psychMovie.local_poster;
    psychPoster.alt = `Poster for ${psychMovie.Title}`;

    // Fill in the template for movie recommendations
    const movieContent = template({
        h2: "Movie Recommendations",
        p: `
            <p><b>Based on your preferred career:</b></p>
            <p><i>${jobMovie.Title}</i> (${jobMovie.Year})</p>
            <span id="job-poster"></span>
            <p><i>${jobMovie.Plot}</i></p>
            <p>(Rated: ${jobMovie.Rated})</p>
            <p><b>Based on your responses:</b></p>
            <p><i>${psychMovie.Title}</i> (${psychMovie.Year})</p>
            <span id="psych-poster"></span>
            <p><i>${psychMovie.Plot}</i></p>
            <p>(Rated: ${psychMovie.Rated})</p>`,
        type: "movie", score: movieScore, verdict: movieVerdict
    });

    // Pet images, if any
    const petContainer = document.createElement('div');
    petContainer.className = 'info-container';
    petContainer.id = 'pet-container';
    petContainer.innerHTML = '<h2>Pet Images</h2>';

    const petAdj = ['magnificent', 'stunning', 'beautiful'];
    let i = 0, showPets = false;
    for (const pet in pets) {
        petContainer.innerHTML += `<p>A <i>${petAdj[i]}</i> <b>${pet}</b>:</p>`;
        const petImg = document.createElement('img');
        petImg.src = pets[pet];
        petImg.alt = `An image of a ${pet}`;
        petContainer.appendChild(petImg);
        i+=1, showPets = true;  // Not reached if no pets were checked
    }

    // Prepare all of the above content
    const profileContainer = document.createElement('div');
    profileContainer.id = 'profile-container';

    // Left column
    const leftCol = document.createElement('div');
    leftCol.id = 'left-col';
    leftCol.innerHTML = jobContent;
    if (showPets) leftCol.appendChild(petContainer);
    profileContainer.appendChild(leftCol);

    // Right column
    profileContainer.innerHTML += movieContent;

    // Prepare a header, include a greeting if provided a name
    const greeting = name != '' ? `Hi ${name}. ` : '';
    const header = `<h2 class="view-header">${greeting}Welcome to your profile.</h2>`;

    // Insert profile into the DOM
    const container = document.getElementById('mydiv1');
    container.innerHTML = header;
    container.appendChild(profileContainer);
    document.getElementById("job-poster").appendChild(jobPoster);
    document.getElementById("psych-poster").appendChild(psychPoster);

    // Set suitability score colours
    document.getElementById("job-suitability").style.backgroundColor = jobColour;
    document.getElementById("movie-suitability").style.backgroundColor = movieColour;
}


// Called by the View Profile button
async function viewProfile() {
    await resetAllButtons();

    const data = await fetchData('/view/profile');
    if (!data) return;
    
    await insertProfile(data);

    await activateButton('viewProfile');
    await insertScrollButton('mydiv1');
}

