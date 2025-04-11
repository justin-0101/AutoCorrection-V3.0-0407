@echo off
echo Start generating SVG flowcharts...

mmdc -i main_workflow.mmd -o diagrams\main_workflow.svg -t neutral -b transparent
echo Main workflow chart generated

mmdc -i detailed_workflow.mmd -o diagrams\detailed_workflow.svg -t neutral -b transparent
echo Detailed workflow chart generated

mmdc -i state_diagram.mmd -o diagrams\state_diagram.svg -t neutral -b transparent
echo State diagram generated

mmdc -i data_flow.mmd -o diagrams\data_flow.svg -t neutral -b transparent
echo Data flow chart generated

mmdc -i error_handling.mmd -o diagrams\error_handling.svg -t neutral -b transparent
echo Error handling chart generated

echo All SVG flowcharts generated successfully in 'diagrams' folder! 