const imgD = document.getElementById('img_div');

function animation() {
    let ind = 0;
    function moveR() {
        const r = setInterval(() => { 
            ind++
            
            imgD.style.left = ind+'%';
            if(ind===25){
                clearInterval(r)
            }
        }, 100);
        
    }
    function moveL() {
        const l = setInterval(() => { 
            ind--
            
            imgD.style.left = ind+'%';
            if(ind===0){
                clearInterval(l)
            }
        }, 100);
        
    }
    
    
    setInterval(() => {
        if (ind >= 19) {
            moveL();
        }else{
            moveR();
        }
    }, 2600);
}
animation()
