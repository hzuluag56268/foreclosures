
var getData = function(){
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
    var nombre = document.getElementById('nombre').value;
    var razaM = document.getElementById('raza').value;
    var edadM = document.getElementById('edad').value;
    var colorM = document.getElementById('color').value;
    var telefonoM = document.getElementById('telefono').value;
    var ciudadM = document.getElementById('ciudad').value;
    if (nombre == ""){
        document.getElementById('nombre').focus();
    } else {
        if (razaM == ""){
            document.getElementById('raza').focus();
    } else{
        if (edadM == ""){
            document.getElementById('edad').focus();
    } else{
        if (colorM == ""){
            document.getElementById('color').focus();
    } else{ 
        if (telefonoM == ""){
            document.getElementById('telefono').focus();
        } else{
            if (ciudadM == ""){
                document.getElementById('ciudad').focus();
                console.log('work');
    } else {    
        console.log(nombre+" "+razaM+" "+edadM+" "+colorM+" "+telefonoM+" "+ciudadM)
        var dataDict = {
            nombre_mascota: nombre,
            raza: razaM,
            edad: edadM,
            color: colorM,
            telefono: telefonoM,
            ciudad: ciudadM,
        };
        saveOne('http://127.0.0.1:8002/api/pets', dataDict);    
        
        document.getElementById('nombre').value = "";
        razaM =  document.getElementById('raza').value = "";
        edadM =  document.getElementById('edad').value = "";
        colorM =  document.getElementById('color').value = "";
        telefonoM =  document.getElementById('telefono').value = "";
        ciudadM =  document.getElementById('ciudad').value = ""; 
        document.getElementById('nombre').focus();
        }
    }
}
    }
}
    }

}
