document.addEventListener('DOMContentLoaded', function() {
  const switchMonth = document.getElementById('bootstrapSwitch');
  const linkSwitchs = document.querySelectorAll('.linkSwitch');

  switchMonth.addEventListener('change',()=>{
    if (switchMonth.checked){
      console.log('一括前月モードON');
    }
    linkSwitchs.forEach(element => {
      const url = switchMonth.checked ? element.dataset.prev : element.dataset.current;
      element.href = url;
    });
})});