import React from "react";
import ReactDOM from "react-dom";
import KintoAdmin from "kinto-admin";
import * as signoffPlugin from "kinto-admin/lib/plugins/signoff";


ReactDOM.render(
  <KintoAdmin plugins={[signoffPlugin]} />,
  document.getElementById("root")
);
