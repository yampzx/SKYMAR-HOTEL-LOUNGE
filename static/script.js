
const entrada = document.getElementById('entrada');
const salida = document.getElementById('salida');

const formulario = document.getElementById('bookingForm');
const nombreCliente = document.getElementById('nombreCliente');
const correoCliente = document.getElementById('correoCliente');
const telefonoCliente = document.getElementById('telefonoCliente');

const hoy = new Date();

const fechaLocal = new Date(
  hoy.getTime() - hoy.getTimezoneOffset() * 60000
).toISOString().slice(0, 10);

// Evitar fechas anteriores al día actual.
entrada.min = fechaLocal;
salida.min = fechaLocal;

// Ajustar la fecha mínima de salida según la entrada.
entrada.addEventListener('change', () => {
  salida.min = entrada.value || fechaLocal;

  if (salida.value && salida.value <= entrada.value) {
    salida.value = '';
  }
});

// Procesar la solicitud demostrativa.
formulario.addEventListener('submit', (event) => {
  event.preventDefault();

  if (!formulario.reportValidity()) {
    return;
  }

  if (entrada.value < fechaLocal) {
    alert('La fecha de entrada no puede ser anterior al día de hoy.');
    return;
  }

  if (salida.value <= entrada.value) {
    alert('La fecha de salida debe ser posterior a la fecha de entrada.');
    return;
  }

  const nombre = nombreCliente.value.trim();
  const correo = correoCliente.value.trim();
  const telefono = telefonoCliente.value.trim();
  const cantidadHuespedes = Number(
    document.getElementById('huespedes').value
  );
  const habitacion = document.getElementById('tipo').value;

  if (!nombre || !correo || !telefono) {
    alert('Completa todos los datos del cliente.');
    return;
  }

  // Validar capacidad según el tipo de habitación elegido.
  // Validar capacidad según el tipo de habitación elegido.
  if (
    (habitacion === 'Estándar' || habitacion === 'Deluxe') &&
    cantidadHuespedes > 2
  ) {
    alert(
      'Las habitaciones Estándar y Deluxe admiten máximo 2 personas. ' +
      'Selecciona la habitación Familiar o reduce la cantidad de huéspedes.'
    );
    return;
  }

  // Si todas las validaciones son correctas, enviamos el formulario a Flask
  formulario.submit();
});

// Mantener el funcionamiento de los botones de las habitaciones.
document.querySelectorAll('.choose-room').forEach(button => {
  button.addEventListener('click', () => {
    document.getElementById('tipo').value = button.dataset.room;

    document.getElementById('reservar').scrollIntoView({
      behavior: 'smooth'
    });
  });
});