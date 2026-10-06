/*
function showAll(url) {
    fetch(url)
    .then(response => response.json())
    .then(data => console.log(data))
}
showAll('http://127.0.0.1:8000/api/products');
function showOne(url, idNum) {
    fetch(url+ idNum)
    .then(response => response.json())
    .then(data => console.log(data))
}
//showOne('http://127.0.0.1:8000/api/products/', '9');

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
//destroy('http://127.0.0.1:8000/api/products/', '7');

function saveOne(url) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type':'application/json'
        },
        body : JSON.stringify({
            fn : 'listnewuuu'
        })
    }).then(res => res.json())
    .catch(error => console.error('Error:', error))
    .then(response => console.log('Success:', response));
}
//saveOne('http://127.0.0.1:8000/api/products');

function update(url, idNum) {
    fetch(url + idNum, {
        method: 'PUT',
        headers: {
            'Content-Type':'application/json'
        },
        body : JSON.stringify({
            fn : '5555555'
        })
    }).then(res => res.json())
    .catch(error => console.error('Error:', error))
    .then(response => console.log('Success:', response));
}
//update('http://127.0.0.1:8000/api/products/' + '27');
*/

function showAll(url) {
    fetch(url)
    .then(response => response.json())
    .then(data => console.log(data))
}
//showAll('http://127.0.0.1:8002/api/pets');

function showOne(url, idNum) {
    fetch(url+ idNum)
    .then(response => response.json())
    .catch(error => console.error('Error:', `Pet ${idNum} not found`))
    .then(data => console.log(data))
}
//showOne('http://127.0.0.1:8002/api/pets/', '12');
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
//destroy('http://127.0.0.1:8002/api/pets/', '1');
const petDataDict = {
    nombre_mascota: "1000-",
    raza: "nn",
    edad: 4441,
    color: "nn",
    telefono: "nn",
    ciudad: "nn" 
}
/*var listPetResults = [
    {
        id: 101,
        nombre_mascota: "n1",
        raza: "nn",
        edad: 4441,
        color: "nn",
        telefono: "nn",
        ciudad: "nn" 
    },
    {
        id: 102,
        nombre_mascota: "n2",
        raza: "nn2",
        edad: 4441,
        color: "nn2",
        telefono: "2nn",
        ciudad: "nn2" 
    },
    {
        id: 103,
        nombre_mascota: "n3",
        raza: "nn3",
        edad: 44413,
        color: "nn3",
        telefono: "3nn",
        ciudad: "nn3" 
    }
] */
/* for(let i=1; i<10;i++){
    saveOne('http://127.0.0.1:8002/api/pets', petDataDict);
}
*/
function saveOne(url, newPetDataDict ) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type':'application/json'
        },
        body : JSON.stringify(newPetDataDict
           /*  {
            nombre_mascota: "10",
            raza: "fr4ecffdnch",
            edad: 4441,
            color: "yefl4xffsdlow",
            telefono: "304f44509987640",
            ciudad: "cagf4ff44gfli"
            } */
        )
    }).then(res => res)
    .catch(error => console.error('Error:', error))
    .then(response => console.log(response));
    //showAll('http://127.0.0.1:8002/api/pets');  
}
//saveOne('http://127.0.0.1:8002/api/pets', petDataDict);
//showAll('http://127.0.0.1:8002/api/pets');
const dictWithUpdate = {
    nombre_mascota: "prueba2",
    edad: 3,
    color: "yellow"
};
function update(url, idNum, dictWithUpdateData) {
    fetch(url + idNum, {
        method: 'PUT',
        headers: {
            'Content-Type':'application/json'
        },
        body : JSON.stringify(dictWithUpdateData)
    }).then(res => res.json())
    .catch(error => console.error('Error:', error))
    .then(response => console.log('Success:', response));
}
//update('http://127.0.0.1:8002/api/pets/', '12', dictWithUpdate);
/* for(let i=1;i<1;i++){
    showOne('http://127.0.0.1:8002/api/pets/', i);
} */