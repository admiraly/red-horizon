#version 450 core
in vec3 colour;
in float distanceFog;
uniform vec4 weather;
uniform int meshMode;
out vec4 outputColour;
void main(){float fog=(meshMode==1||meshMode==2)?0.:1.-exp(-distanceFog*(.00018+weather.w));vec3 fogColour=mix(vec3(.49,.61,.68),vec3(.49,.53,.55),weather.y);outputColour=vec4(mix(colour,fogColour,fog),1);}
