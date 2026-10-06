let cardC = document.getElementById('card_container');

function showData(dictList) {
    dictList.forEach(pet => {
        let htmlText = `
            <div class="card" >
            <img src="https://images.unsplash.com/photo-1583337130417-3346a1be7dee?ixid=MnwxMjA3fDB8MHxzZWFyY2h8MXx8cGV0c3xlbnwwfHwwfHw%3D&ixlib=rb-1.2.1&auto=format&fit=crop&w=400&q=60" alt="pet">
            <p class="description">
                Hola,  Soy <strong>${pet.nombre_mascota}</strong>. <br>
                Soy un lindo <strong>${pet.raza}</strong>. <br>
                Color <strong>${pet.color}</strong> . <br>
                Tengo  <strong>${pet.edad}</strong> añitos. <br> 
                Vivo en <strong>${pet.ciudad}</strong>.  <br>
            </p>
            <p class="tel">
                <strong> ${pet.telefono} :)</strong>   <br>
                <button id=${pet.id} class="btn" onclick="errase(${pet.id})">Eliminar</button>

            </p>
            </div>
        `
        cardC.insertAdjacentHTML('afterbegin', htmlText)
        console.log(pet.raza);
    });
    
}

function showAll(url) {
    fetch(url)
    .then(response => response.json())
    .then(data => showData(data))
}
showAll('http://127.0.0.1:8002/api/pets');


function errase(e) {
    function destroy(url, idNum) {
        fetch(url + idNum, {
            method: 'DELETE',
            headers: {
                'Content-Type':'application/json'
            }
        })
        .then(response => response.json())
        .then(data => console.log(data))
    }
    destroy('http://127.0.0.1:8002/api/pets/', e);
}