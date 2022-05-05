console.log("Extra")

const btns = document.querySelectorAll('.appointment')
const day = document.querySelector('#day_selected')
const time = document.querySelector('#time_selected')

console.log(btns)


btns.forEach(btn => {
    btn.addEventListener('click', () => {
        day.value = btn.dataset.day
        time.value = btn.dataset.time
        }
        )

})