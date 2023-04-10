let dataset_list = {};
let general_settings = {};
let is_received_initial_settings = false;
let unix_before_graph_updated = new Date().getTime();

function show_error(e) {
  console.error(e);
}

document.addEventListener("DOMContentLoaded", function () {
  try {
    console.log("DOM fully loaded and parsed");

    // Prevent page reload
    window.addEventListener("beforeunload", function (e) {
      e.preventDefault();
      e.returnValue = "本当に閉じますか？ウィンドウを閉じても、ロギングは継続されます。";
    });
  } catch (e) {
    show_error(e);
  }
});

// Receive data from python (initialize)
eel.expose(Get_Initial_Settings);
function Get_Initial_Settings(provided_setting_dict) {
  try {
    console.log("Initialize start");

    Object.keys(provided_setting_dict).forEach(function (id) {
      general_settings[id] = provided_setting_dict[id];
    });
    // Initialize dataset_list
    Object.keys(general_settings.data_list).forEach(function (id) {
      dataset_list[id] = general_settings.data_list[id];
      dataset_list[id]["chart_obj"] = undefined;
      dataset_list[id]["data"] = [];
    });

    // Insert elements in container
    const containers = document.getElementById("graphs");
    const indicators = document.getElementById("indicators");
    Object.keys(dataset_list).forEach(function (id) {
      containers.innerHTML += `\
      <div class="container container_${id}">\
        <div class="labels">\
          <span class="name">${dataset_list[id].display_name}</span>\
          <span class="value value_${id}">1,234</span>\
          <span class="unit">${dataset_list[id].unit}</span>\
        </div>\
        <div class="chart">\
          <canvas id="chart_${id}"></canvas>\
        </div>\
      </div>\
      `;
      indicators.innerHTML += `\
      <div class="labels indicator indicator_${id}">\
        <span class="name">${dataset_list[id].display_name}</span>\
        <br>\
        <span class="value value_${id}">1,234</span>\
        <span class="unit">${dataset_list[id].unit}</span>\
      </div>\
      `;
    });

    // Enable each graphs
    Object.keys(dataset_list).forEach(function (id) {
      let this_canvas = document.getElementById(`chart_${id}`).getContext("2d");
      dataset_list[id].chart_obj = new Chart(this_canvas, {
        type: "line",
        data: {
          labels: [],
          datasets: [
            {
              label: "Value",
              data: dataset_list[id].data,
              borderWidth: 1,
              borderColor: "rgb(255, 99, 132)",
            },
          ],
        },
        options: {
          pointRadius: 0,
          animation: {
            duration: 0,
          },
          responsive: true,
          plugins: {
            legend: {
              display: false,
            },
          },
          scales: {
            x: {
              // min: 0,
              // max: general_settings.interface.graph_max_display,
              display: true,
            },
            y: {
              // min: 0,
              // max: 100,
              display: true,
            },
          },
        },
      });
    });

    console.log("Initialize done");
    is_received_initial_settings = true;
  } catch (e) {
    show_error(e);
  }
}

// Receive data from python (update data)
eel.expose(Data_PY2JS);
function Data_PY2JS(data) {
  try {
    if (!is_received_initial_settings) {
      return;
    }
    throw new Error("Data_PY2JS is not implemented");
    // 前回のグラフ更新から一定時間が経たないとグラフが更新しない（描画処理の負荷軽減）
    let is_do_update_graph = false;
    if (new Date().getTime() - unix_before_graph_updated > general_settings.interface.update_interval_sec * 1000) {
      is_do_update_graph = true;
      unix_before_graph_updated = new Date().getTime();
    }

    Object.keys(data).forEach(function (id) {
      if (Object.keys(dataset_list).includes(id)) {
        let new_data = data[id];
        dataset_list[id].data.push(new_data);
        dataset_list[id].chart_obj.data.labels.push("");

        if (dataset_list[id].data.length > general_settings.interface.graph_max_display) {
          dataset_list[id].data.shift();
          dataset_list[id].chart_obj.data.labels.shift();
        }

        if (is_do_update_graph) {
          dataset_list[id].chart_obj.update();
        }

        Array.from(document.getElementsByClassName(`value_${id}`)).forEach((element) => {
          element.innerHTML = new_data;
        });

        Array.from(document.getElementsByClassName(`indicator_${id}`)).forEach((element) => {
          if (dataset_list[id].safe_range_max < new_data) {
            element.classList.add("danger");
            element.classList.remove("safe");
          } else if (dataset_list[id].safe_range_min > new_data) {
            element.classList.add("danger");
            element.classList.remove("safe");
          } else {
            element.classList.remove("danger");
            element.classList.add("safe");
          }
        });
      }
    });
  } catch (e) {
    show_error(e);
  }
}

function header_hide() {
  try {
    document.getElementById("header_on_hidden").style.display = "none";
    document.getElementById("header_on_shown").style.display = "flex";
  } catch (e) {
    show_error(e);
  }
}
function header_show() {
  try {
    document.getElementById("header_on_hidden").style.display = "flex";
    document.getElementById("header_on_shown").style.display = "none";
  } catch (e) {
    show_error(e);
  }
}
