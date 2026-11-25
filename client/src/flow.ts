// Данные между экранами входа (только в памяти приложения).
export const flow = {
  email: "",
  registrationToken: "",
  reset() {
    this.email = "";
    this.registrationToken = "";
  },
};
